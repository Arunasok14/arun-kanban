from __future__ import annotations
import asyncio
import json
import re
from datetime import datetime, timezone
from typing import Optional, AsyncGenerator

import httpx

from agent_adapters.claude_adapter import ClaudeCodeAdapter
from agent_adapters.codex_adapter import CodexAdapter
from agent_adapters.gemini_adapter import GeminiAdapter
from agent_adapters.base import AgentAdapter
from agent_adapters.types import AgentStatus, AgentEvent, EventLevel

from .config import settings
from .context_injector import ContextInjector
from .docker_runner import stream_container, is_docker_available, image_exists
from .process_manager import process_manager
from .worktree_manager import WorktreeManager
from . import approval_registry

worktree_manager = WorktreeManager()
context_injector = ContextInjector()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _post_event(client: httpx.AsyncClient, execution_id: str, event_data: dict) -> None:
    try:
        await client.post(
            f"{settings.api_url}/api/internal/executions/{execution_id}/events",
            json=event_data,
            timeout=10.0,
        )
    except Exception as e:
        print(f"[runner] Failed to post event for {execution_id}: {e}")


async def _post_tokens(client: httpx.AsyncClient, execution_id: str, token_data: dict) -> dict:
    """POST token update; returns response JSON (includes budget_exhausted flag)."""
    try:
        r = await client.post(
            f"{settings.api_url}/api/internal/executions/{execution_id}/tokens",
            json=token_data,
            timeout=10.0,
        )
        return r.json()
    except Exception as e:
        print(f"[runner] Failed to post tokens for {execution_id}: {e}")
        return {}


# Per-million-token cost (input, output) in USD
MODEL_COSTS: dict[str, tuple[float, float]] = {
    "sonnet": (3.00, 15.00),
    "opus": (15.00, 75.00),
    "haiku": (0.25, 1.25),
}


def _compute_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    in_rate, out_rate = MODEL_COSTS.get(model, (3.00, 15.00))
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000


async def _post_status(client: httpx.AsyncClient, execution_id: str, status_data: dict) -> None:
    try:
        await client.post(
            f"{settings.api_url}/api/internal/executions/{execution_id}/status",
            json=status_data,
            timeout=10.0,
        )
    except Exception as e:
        print(f"[runner] Failed to post status for {execution_id}: {e}")


def _build_adapter(
    agent: str,
    model: str,
    max_budget_usd: float,
    openai_api_key: str = "",
    gemini_api_key: str = "",
    skip_permissions: bool = True,
) -> AgentAdapter:
    if agent == "codex":
        return CodexAdapter(api_key=openai_api_key, model=model)
    if agent == "gemini":
        return GeminiAdapter(api_key=gemini_api_key, model=model)
    # Default: claude-code
    return ClaudeCodeAdapter(
        model=model,
        max_budget_usd=max_budget_usd,
        claude_bin=settings.claude_bin,
        skip_permissions=skip_permissions,
        approval_callback=approval_registry.request_approval if not skip_permissions else None,
        api_url=settings.api_url,
    )


def _parse_test_results(log_lines: list[str]) -> dict:
    """
    Parse test output collected from validation execution logs.
    Supports mocha/jest/pytest patterns and our explicit RESULTS: line.
    """
    passed = 0
    failed = 0
    errors = 0
    details: list[str] = []

    for line in log_lines:
        # Explicit summary line: RESULTS: N passed, M failed, E errors
        m = re.search(r"RESULTS:\s*(\d+)\s*passed,\s*(\d+)\s*failed,\s*(\d+)\s*errors", line, re.IGNORECASE)
        if m:
            passed, failed, errors = int(m.group(1)), int(m.group(2)), int(m.group(3))
            continue
        # Jest/mocha: "12 passing" / "3 failing"
        m = re.search(r"(\d+)\s+passing", line)
        if m:
            passed = int(m.group(1))
        m = re.search(r"(\d+)\s+failing", line)
        if m:
            failed = int(m.group(1))
        # pytest: "3 failed, 12 passed"
        m = re.search(r"(\d+)\s+failed", line)
        if m:
            failed = int(m.group(1))
        m = re.search(r"(\d+)\s+passed", line)
        if m:
            passed = int(m.group(1))
        # Capture individual failures (lines starting with ✗ or "FAIL ")
        if re.match(r"\s*(✗|FAIL|×)\s+", line):
            details.append(line.strip()[:120])

    return {"passed": passed, "failed": failed, "errors": errors, "details": details[:20]}


async def _docker_event_stream(
    prompt: str,
    worktree_path: str,
    agent: str,
    model: str,
    openai_api_key: str,
    gemini_api_key: str,
    skip_permissions: bool,
) -> AsyncGenerator[AgentEvent, None]:
    """
    Run the agent inside a Docker container and yield AgentEvent objects.
    Lines are streamed as stdout-level events; no structured JSON parsing
    (token tracking not available in Docker mode for non-Claude agents).
    """
    import os

    # Build the CLI invocation for the chosen agent
    if agent == "codex":
        command = ["codex", "--approval-mode", "full-auto", "--quiet", prompt]
        env = {
            "OPENAI_API_KEY": openai_api_key,
            "NO_COLOR": "1",
        }
    elif agent == "gemini":
        command = ["gemini", "--model", "gemini-2.0-flash", "--yolo", prompt]
        env = {
            "GEMINI_API_KEY": gemini_api_key,
            "NO_COLOR": "1",
        }
    else:
        # claude-code
        flags = [
            "--output-format", "stream-json",
            "--model", model,
        ]
        if skip_permissions:
            flags += ["--dangerously-skip-permissions"]
        command = ["claude"] + flags + [prompt]
        env = {
            "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", ""),
            "NO_COLOR": "1",
        }

    seq = 0
    async for line in stream_container(
        command=command,
        worktree_path=worktree_path,
        env=env,
        image=settings.docker_image,
        mem_limit=settings.docker_mem_limit,
        cpu_quota=settings.docker_cpu_quota,
    ):
        yield AgentEvent(
            sequence=seq,
            level=EventLevel.STDOUT,
            content=line,
            timestamp=_now(),
            raw_json=None,
        )
        seq += 1


async def run_execution(
    execution_id: str,
    task_id: str,
    task_title: str,
    task_description: str,
    worktree_path: Optional[str],
    branch_name: Optional[str],
    repo_path: Optional[str],
    project_name: Optional[str],
    base_branch: str = "main",
    prompt_override: Optional[str] = None,
    agent: str = "claude-code",
    model: str = "sonnet",
    max_budget_usd: float = 2.0,
    openai_api_key: str = "",
    gemini_api_key: str = "",
    skip_permissions: bool = True,
    skip_worktree_commit: bool = False,
    skip_context_inject: bool = False,
    impl_execution_id: Optional[str] = None,
    use_docker: bool = False,
    prior_work: Optional[list] = None,
) -> None:
    """
    Main execution coroutine. Runs in the background.
    1. Creates worktree if needed
    2. Injects context (with optional prior-work section from Sprint 5)
    3. Runs agent (native subprocess or Docker container)
    4. Streams events back to API
    5. Auto-commits changes
    """
    async with httpx.AsyncClient() as client:
        # Signal: running
        await _post_status(client, execution_id, {
            "status": "running",
            "started_at": _now(),
        })

        try:
            # Step 1: Ensure worktree exists
            if not worktree_path and repo_path:
                try:
                    worktree_path, branch_name = await worktree_manager.create_worktree(
                        repo_path=repo_path,
                        project_name=project_name or task_id,
                        task_id=task_id,
                        task_title=task_title,
                        base_branch=base_branch,
                    )
                except Exception as e:
                    await _post_status(client, execution_id, {
                        "status": "failed",
                        "error_message": f"Failed to create worktree: {e}",
                        "finished_at": _now(),
                    })
                    return

            if not worktree_path:
                await _post_status(client, execution_id, {
                    "status": "failed",
                    "error_message": "No worktree_path provided and no repo_path to create one",
                    "finished_at": _now(),
                })
                return

            # Step 2: Inject context
            if skip_context_inject:
                prompt = prompt_override or f"# Task: {task_title}\n\n{task_description}"
            else:
                prompt = prompt_override or context_injector.inject(
                    worktree_path=worktree_path,
                    task_id=task_id,
                    title=task_title,
                    description=task_description,
                    branch_name=branch_name or "unknown",
                    base_branch=base_branch,
                    prior_work=prior_work or [],
                )

            # Step 3: Build adapter (always needed — registers PID, handles stop())
            adapter = _build_adapter(
                agent=agent,
                model=model,
                max_budget_usd=max_budget_usd,
                openai_api_key=openai_api_key,
                gemini_api_key=gemini_api_key,
                skip_permissions=skip_permissions,
            )
            process_manager.register(execution_id, adapter)

            # Record budget_usd on the execution
            await _post_status(client, execution_id, {
                "status": "running",
                "budget_usd": max_budget_usd,
            })

            # Step 3b: Validate Docker readiness; fall back gracefully if not ready
            if use_docker:
                if not is_docker_available():
                    await _post_event(client, execution_id, {
                        "sequence": 0,
                        "level": "system",
                        "content": "[docker] Docker daemon not reachable — falling back to host execution",
                        "timestamp": _now(),
                    })
                    use_docker = False
                elif not image_exists(settings.docker_image):
                    await _post_event(client, execution_id, {
                        "sequence": 0,
                        "level": "system",
                        "content": (
                            f"[docker] Image '{settings.docker_image}' not found. "
                            "Build it: docker build -f Dockerfile.agent -t kanban-agent:latest . "
                            "— falling back to host execution"
                        ),
                        "timestamp": _now(),
                    })
                    use_docker = False
                else:
                    await _post_event(client, execution_id, {
                        "sequence": 0,
                        "level": "system",
                        "content": f"[docker] Running in container: {settings.docker_image}",
                        "timestamp": _now(),
                    })

            # Step 4: Choose event source
            if use_docker:
                event_source = _docker_event_stream(
                    prompt=prompt,
                    worktree_path=worktree_path,
                    agent=agent,
                    model=model,
                    openai_api_key=openai_api_key,
                    gemini_api_key=gemini_api_key,
                    skip_permissions=skip_permissions,
                )
            else:
                event_source = adapter.run(prompt, worktree_path, execution_id)

            # Track state during streaming
            pid_reported = False
            exit_code = None
            token_usage = None
            final_status = AgentStatus.COMPLETED
            total_input = 0
            total_output = 0
            budget_exhausted = False
            log_lines: list[str] = []

            async for event in event_source:
                # Capture PID from system event (native adapter only)
                if not pid_reported and event.raw_json and event.raw_json.get("pid"):
                    await _post_status(client, execution_id, {
                        "status": "running",
                        "pid": event.raw_json["pid"],
                        "started_at": _now(),
                    })
                    pid_reported = True

                # Capture exit info from terminal system event
                if event.raw_json and event.raw_json.get("type") == "process_exit":
                    exit_code = event.raw_json.get("exit_code")
                    final_status = event.raw_json.get("status", AgentStatus.COMPLETED)

                # Report token usage incrementally and enforce budget (native adapter only)
                if event.raw_json and event.raw_json.get("type") == "usage":
                    inp = event.raw_json.get("input_tokens", 0)
                    out = event.raw_json.get("output_tokens", 0)
                    total_input += inp
                    total_output += out
                    cost_delta = _compute_cost(model, inp, out)
                    total_cost = _compute_cost(model, total_input, total_output)
                    budget_exhausted = total_cost >= max_budget_usd
                    await _post_tokens(client, execution_id, {
                        "input_tokens": inp,
                        "output_tokens": out,
                        "cost_usd": cost_delta,
                        "budget_exhausted": budget_exhausted,
                    })
                    token_usage = {"input": total_input, "output": total_output, "total": total_input + total_output}
                    if budget_exhausted:
                        await adapter.stop(execution_id)
                        final_status = AgentStatus.STOPPED
                        break

                # Collect log lines for test result parsing (validation runs)
                if event.content:
                    log_lines.append(event.content)

                await _post_event(client, execution_id, {
                    "sequence": event.sequence,
                    "level": event.level,
                    "content": event.content,
                    "timestamp": event.timestamp,
                })

            # Step 5: Auto-commit + push branch (skipped for validation runs)
            if not skip_worktree_commit:
                try:
                    commit_sha = await worktree_manager.commit_changes(
                        worktree_path=worktree_path,
                        message=f"feat: {task_title}\n\nTask ID: {task_id}\nExecution ID: {execution_id}",
                    )
                    if commit_sha:
                        await _post_event(client, execution_id, {
                            "sequence": 999999,
                            "level": "system",
                            "content": f"Auto-committed changes: {commit_sha[:12]}",
                            "timestamp": _now(),
                        })
                        # Push branch to origin for PR creation
                        if branch_name:
                            pushed = await worktree_manager.push_branch(
                                worktree_path=worktree_path,
                                branch_name=branch_name,
                            )
                            if pushed:
                                await _post_event(client, execution_id, {
                                    "sequence": 999998,
                                    "level": "system",
                                    "content": f"Pushed branch: {branch_name}",
                                    "timestamp": _now(),
                                })
                except Exception as e:
                    print(f"[runner] Auto-commit failed for {execution_id}: {e}")

            # Step 6: Final status
            await _post_status(client, execution_id, {
                "status": str(final_status),
                "exit_code": exit_code,
                "token_usage": token_usage,
                "finished_at": _now(),
            })

            # Step 7: Post validation results (validation runs only)
            if impl_execution_id:
                test_results = _parse_test_results(log_lines)
                try:
                    await client.post(
                        f"{settings.api_url}/api/internal/executions/{impl_execution_id}/validation_result",
                        json=test_results,
                        timeout=10.0,
                    )
                except Exception as e:
                    print(f"[runner] Failed to post validation result for {impl_execution_id}: {e}")

        except asyncio.CancelledError:
            await _post_status(client, execution_id, {
                "status": "stopped",
                "finished_at": _now(),
            })
        except Exception as e:
            await _post_status(client, execution_id, {
                "status": "failed",
                "error_message": str(e),
                "finished_at": _now(),
            })
        finally:
            process_manager.unregister(execution_id)
