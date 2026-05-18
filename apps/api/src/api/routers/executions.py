from __future__ import annotations
import asyncio
import re
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
import httpx
from ..database import get_db
from ..schemas import (
    ExecutionCreate, Execution, InternalEventCreate,
    InternalStatusUpdate, InternalTokenUpdate, InternalValidationResult,
)
from ..services import execution_service, task_service, settings_service, project_service, embedding_service
from ..services import github_service, vercel_service
from ..config import settings
from .. import queue as task_queue

router = APIRouter(tags=["executions"])


@router.post("/api/v1/tasks/{task_id}/executions", response_model=Execution, status_code=201)
async def start_execution(task_id: str, data: ExecutionCreate):
    async with get_db() as db:
        task = await task_service.get(db, task_id)
        if not task:
            raise HTTPException(404, "Task not found")
        project = await project_service.get(db, task.project_id)
        execution = await execution_service.create(db, task_id, task.agent)

        # Read defaults from settings (fall back if key missing)
        default_model = await settings_service.get_value(db, "default_model", "sonnet")
        default_budget = await settings_service.get_value(db, "default_budget_usd", "2.00")
        openai_api_key = await settings_service.get_value(db, "openai_api_key", "")
        gemini_api_key = await settings_service.get_value(db, "gemini_api_key", "")
        require_approval = await settings_service.get_value(db, "require_approval", "false")
        docker_sandbox = await settings_service.get_value(db, "docker_sandbox", "false")

        # Sprint 5: retrieve similar prior work for context injection
        query = f"{task.title} {task.description or ''}"
        prior_work = await embedding_service.retrieve_similar(db, query, k=5, api_key=openai_api_key)

    # Resolve model: per-execution override > stage default > global default
    _stage_model_key = {
        "plan":        "stage_model_plan",
        "in_progress": "stage_model_in_progress",
        "testing":     "stage_model_testing",
    }.get(task.status)
    async with get_db() as db:
        stage_default = await settings_service.get_value(db, _stage_model_key, default_model) if _stage_model_key else default_model
    model = data.model_override or stage_default
    budget = data.budget_override or float(default_budget)

    # Enqueue for runtime-manager to pick up
    payload = {
        "execution_id": execution.id,
        "task_id": task_id,
        "task_title": task.title,
        "task_description": task.description or "",
        "prompt_override": data.prompt_override,
        "agent": task.agent,
        "model": model,
        "max_budget_usd": budget,
        "openai_api_key": openai_api_key,
        "gemini_api_key": gemini_api_key,
        "worktree_path": task.worktree_path,
        "branch_name": task.branch_name,
        "repo_path": project.repo_path if project else None,
        "project_name": project.name if project else None,
        "base_branch": project.default_branch if project else "main",
        "skip_permissions": require_approval.lower() != "true",
        "use_docker": docker_sandbox.lower() == "true",
        "prior_work": prior_work,
    }
    try:
        await task_queue.enqueue(payload)
    except Exception as e:
        async with get_db() as db:
            await execution_service.apply_status(
                db, execution.id,
                InternalStatusUpdate(
                    status="failed",
                    error_message=f"Queue unavailable: {e}",
                ),
            )
        raise HTTPException(503, f"Queue unavailable: {e}")

    return execution


@router.get("/api/v1/executions/{execution_id}", response_model=Execution)
async def get_execution(execution_id: str):
    async with get_db() as db:
        execution = await execution_service.get(db, execution_id)
    if not execution:
        raise HTTPException(404, "Execution not found")
    return execution


@router.get("/api/v1/tasks/{task_id}/executions", response_model=dict)
async def list_executions(task_id: str):
    async with get_db() as db:
        task = await task_service.get(db, task_id)
        if not task:
            raise HTTPException(404, "Task not found")
        executions = await execution_service.list_for_task(db, task_id)
    return {"executions": [e.model_dump() for e in executions]}


@router.post("/api/v1/executions/{execution_id}/stop")
async def stop_execution(execution_id: str):
    async with get_db() as db:
        execution = await execution_service.get(db, execution_id)
    if not execution:
        raise HTTPException(404, "Execution not found")
    if execution.status not in ("pending", "running"):
        raise HTTPException(400, f"Execution is already {execution.status}")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(f"{settings.runtime_manager_url}/stop/{execution_id}")
    except Exception as e:
        raise HTTPException(503, f"Runtime manager unavailable: {e}")
    return {"ok": True}


@router.get("/api/v1/executions/{execution_id}/logs", response_model=dict)
async def get_logs(execution_id: str, after_sequence: int = Query(0)):
    async with get_db() as db:
        execution = await execution_service.get(db, execution_id)
        if not execution:
            raise HTTPException(404, "Execution not found")
        logs = await execution_service.get_logs(db, execution_id, after_sequence)
    terminal = execution.status in ("completed", "failed", "stopped")
    return {
        "logs": [l.model_dump() for l in logs],
        "has_more": not terminal,
    }


# ── Internal endpoints (called by runtime-manager) ────────────────────────────

internal_router = APIRouter(prefix="/api/internal", tags=["internal"])


@internal_router.post("/executions/{execution_id}/events")
async def internal_event(execution_id: str, event: InternalEventCreate):
    from ..bus import event_bus
    async with get_db() as db:
        execution = await execution_service.get(db, execution_id)
        if not execution:
            raise HTTPException(404, "Execution not found")
        log_entry = await execution_service.apply_event(db, execution_id, event)

    await event_bus.publish(execution_id, {
        "type": "log",
        "sequence": log_entry.sequence,
        "level": log_entry.level,
        "content": log_entry.content,
        "timestamp": log_entry.timestamp,
    })
    return {"ok": True}


@internal_router.post("/executions/{execution_id}/tokens")
async def internal_tokens(execution_id: str, update: InternalTokenUpdate):
    from ..bus import event_bus
    async with get_db() as db:
        execution = await execution_service.get(db, execution_id)
        if not execution:
            raise HTTPException(404, "Execution not found")
        execution = await execution_service.update_token_usage(db, execution_id, update)

    await event_bus.publish(execution_id, {
        "type": "tokens",
        "token_input": execution.token_input,
        "token_output": execution.token_output,
        "cost_usd": execution.cost_usd,
        "budget_usd": execution.budget_usd,
        "budget_exhausted": execution.budget_exhausted,
    })
    return {"ok": True, "budget_exhausted": execution.budget_exhausted}


async def _spawn_validation(task_id: str, impl_execution_id: str) -> None:
    """Create and enqueue a validation execution for the completed implementation."""
    from ..bus import event_bus
    try:
        async with get_db() as db:
            task = await task_service.get(db, task_id)
            if not task:
                return
            project = await project_service.get(db, task.project_id)
            val_execution = await execution_service.create(
                db, task_id, agent="claude-code", execution_type="validation"
            )
            default_model = await settings_service.get_value(db, "default_model", "sonnet")
            default_budget = await settings_service.get_value(db, "default_budget_usd", "2.00")

        payload = {
            "execution_id": val_execution.id,
            "task_id": task_id,
            "task_title": task.title,
            "task_description": task.description or "",
            "agent": "claude-code",
            "model": default_model,
            "max_budget_usd": float(default_budget),
            "worktree_path": task.worktree_path,
            "branch_name": task.branch_name,
            "repo_path": project.repo_path if project else None,
            "project_name": project.name if project else None,
            "base_branch": project.default_branch if project else "main",
            "skip_permissions": True,
            "skip_worktree_commit": True,
            "skip_context_inject": True,
            "prompt_override": (
                "Run all tests in this repository. Report results. "
                "Do NOT modify any source files. Only fix test configuration issues "
                "(e.g. missing test script in package.json). "
                "After tests finish, output a summary line exactly like: "
                "RESULTS: N passed, M failed, E errors"
            ),
            "impl_execution_id": impl_execution_id,
        }
        await task_queue.enqueue(payload)

        # Notify UI that validation has started
        await event_bus.publish(impl_execution_id, {
            "type": "validation_started",
            "validation_execution_id": val_execution.id,
        })
    except Exception as e:
        print(f"[executions] Failed to spawn validation for task {task_id}: {e}")


async def _record_context(task_id: str, execution_id: str, status: str) -> None:
    """Persist embedding record for a completed/failed implementation execution."""
    try:
        async with get_db() as db:
            task = await task_service.get(db, task_id)
            if not task:
                return
            openai_api_key = await settings_service.get_value(db, "openai_api_key", "")
            outcome = "success" if status == "completed" else "failure"
            await embedding_service.record_execution(
                db=db,
                task_id=task_id,
                execution_id=execution_id,
                task_title=task.title,
                task_description=task.description or "",
                outcome=outcome,
                test_results=task.test_results,
                api_key=openai_api_key,
            )
    except Exception as e:
        print(f"[executions] Failed to record context for {execution_id}: {e}")


@internal_router.post("/executions/{execution_id}/status")
async def internal_status(execution_id: str, update: InternalStatusUpdate):
    from ..bus import event_bus
    async with get_db() as db:
        execution = await execution_service.get(db, execution_id)
        if not execution:
            raise HTTPException(404, "Execution not found")
        execution = await execution_service.apply_status(db, execution_id, update)

    await event_bus.publish(execution_id, {
        "type": "status",
        "status": execution.status,
        "pid": execution.pid,
        "token_input": execution.token_input,
        "token_output": execution.token_output,
        "cost_usd": execution.cost_usd,
    })

    if execution.status in ("completed", "failed", "stopped"):
        await event_bus.publish_done(execution_id)
        # Auto-spawn validation after successful implementation
        if execution.status == "completed" and execution.execution_type == "implementation":
            asyncio.create_task(_spawn_validation(execution.task_id, execution_id))
        # Sprint 5: record execution outcome for future context retrieval
        if execution.execution_type == "implementation":
            asyncio.create_task(_record_context(execution.task_id, execution_id, execution.status))

    return {"ok": True}


async def _spawn_deployment(
    impl_execution_id: str,
    task_id: str,
) -> None:
    """
    After validation passes: push to GitHub and optionally Vercel.
    Fires-and-forgets from internal_validation_result.
    """
    from ..bus import event_bus
    import subprocess
    try:
        async with get_db() as db:
            task = await task_service.get(db, task_id)
            if not task:
                return
            project = await project_service.get(db, task.project_id)
            github_token = await settings_service.get_value(db, "github_token", "")
            github_repo = await settings_service.get_value(db, "github_repo", "")
            auto_deploy = await settings_service.get_value(db, "auto_deploy", "false")
            vercel_token = await settings_service.get_value(db, "vercel_token", "")
            vercel_project_id = await settings_service.get_value(db, "vercel_project_id", "")
            execution = await execution_service.get(db, impl_execution_id)

        if not github_token or not github_repo or not task.branch_name:
            return  # deployment not configured

        # Build PR body using diff stat from worktree
        diff_stat = ""
        if task.worktree_path and project:
            try:
                proc = await asyncio.create_subprocess_exec(
                    "git", "diff", "--stat", f"{project.default_branch}...HEAD",
                    cwd=task.worktree_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                out, _ = await proc.communicate()
                diff_stat = out.decode("utf-8", errors="replace").strip()
            except Exception:
                pass

        token_input = execution.token_input if execution else 0
        token_output = execution.token_output if execution else 0
        cost_usd = execution.cost_usd if execution else 0.0

        pr_body = github_service.build_pr_body(
            task_title=task.title,
            task_description=task.description or "",
            diff_stat=diff_stat,
            test_results=task.test_results,
            token_input=token_input,
            token_output=token_output,
            cost_usd=cost_usd,
        )

        # Create GitHub PR
        pr_url = await github_service.create_pr(
            repo=github_repo,
            head_branch=task.branch_name,
            base_branch=project.default_branch if project else "main",
            title=task.title,
            body=pr_body,
            token=github_token,
        )

        async with get_db() as db:
            await task_service.set_pr_url(db, task_id, pr_url)

        await event_bus.publish(impl_execution_id, {
            "type": "deployment",
            "pr_url": pr_url,
            "preview_url": None,
        })

        # Vercel preview deploy
        if auto_deploy.lower() == "true" and vercel_token and vercel_project_id:
            deploy_id = await vercel_service.trigger_deploy(
                project_id=vercel_project_id,
                branch=task.branch_name,
                token=vercel_token,
            )
            preview_url = await vercel_service.poll_until_ready(
                deployment_id=deploy_id,
                token=vercel_token,
            )
            if preview_url:
                async with get_db() as db:
                    await task_service.set_preview_url(db, task_id, preview_url)
                await event_bus.publish(impl_execution_id, {
                    "type": "deployment",
                    "pr_url": pr_url,
                    "preview_url": preview_url,
                })

    except Exception as e:
        print(f"[executions] Deployment pipeline failed for task {task_id}: {e}")


@internal_router.post("/executions/{execution_id}/validation_result")
async def internal_validation_result(execution_id: str, result: InternalValidationResult):
    """Called by runtime-manager after parsing test output from a validation execution."""
    from ..bus import event_bus
    async with get_db() as db:
        execution = await execution_service.get(db, execution_id)
        if not execution:
            raise HTTPException(404, "Execution not found")
        results_dict = result.model_dump()
        await task_service.set_test_results(db, execution.task_id, results_dict)

    # Broadcast to implementation execution's WS channel so the panel updates
    await event_bus.publish(execution_id, {
        "type": "test_results",
        "passed": result.passed,
        "failed": result.failed,
        "errors": result.errors,
        "details": result.details,
    })

    # Sprint 7: if all tests pass, trigger GitHub PR + Vercel deploy
    if result.failed == 0 and result.errors == 0 and result.passed > 0:
        asyncio.create_task(_spawn_deployment(execution_id, execution.task_id))

    return {"ok": True}
