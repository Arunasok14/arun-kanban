from __future__ import annotations
import asyncio
import json
import os
import re
import signal
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional, Callable, Awaitable

from .base import AgentAdapter
from .types import AgentEvent, AgentStatus, EventLevel

CLAUDE_BIN = os.environ.get("CLAUDE_BIN", "/opt/homebrew/bin/claude")

# Matches Claude's interactive permission prompts, e.g.:
#   "Do you want to run bash command: `rm -rf /tmp`? [y/n]"
#   "Do you want to create file /path/file.py? [y/n]"
_APPROVAL_RE = re.compile(r"Do you want to .+\? \[y/n\]", re.IGNORECASE)

ApprovalCallback = Callable[[str, str, str, str], Awaitable[bool]]
"""(api_url, execution_id, approval_id, prompt_text) -> approved"""


class ClaudeCodeAdapter(AgentAdapter):
    """
    Invokes the Claude Code CLI with --output-format stream-json and
    streams structured AgentEvents.
    """

    def __init__(
        self,
        model: str = "sonnet",
        max_budget_usd: float = 2.0,
        claude_bin: str = CLAUDE_BIN,
        approval_callback: Optional[ApprovalCallback] = None,
        api_url: str = "",
        skip_permissions: bool = True,
    ):
        self._model = model
        self._max_budget_usd = max_budget_usd
        self._claude_bin = claude_bin
        self._approval_callback = approval_callback
        self._api_url = api_url
        self._skip_permissions = skip_permissions
        self._process: Optional[asyncio.subprocess.Process] = None
        self._pid: Optional[int] = None
        self._sequence: int = 0

    @property
    def pid(self) -> Optional[int]:
        return self._pid

    def _next_seq(self) -> int:
        self._sequence += 1
        return self._sequence

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _build_command(self, prompt: str) -> list[str]:
        cmd = [
            self._claude_bin,
            "--print",
            "--output-format", "stream-json",
            "--no-session-persistence",
            "--model", self._model,
            "--max-budget-usd", str(self._max_budget_usd),
        ]
        if self._skip_permissions:
            cmd.append("--dangerously-skip-permissions")
        cmd.append(prompt)
        return cmd

    def _parse_line(self, line: str) -> AgentEvent:
        """
        Claude stream-json frame types:
          {"type": "text", "text": "..."}
          {"type": "tool_use", "name": "...", "input": {...}}
          {"type": "tool_result", ...}
          {"type": "usage", "input_tokens": N, "output_tokens": M}
          {"type": "result", "exit_code": 0}
          {"type": "assistant", "message": {...}}
        """
        try:
            frame = json.loads(line)
            frame_type = frame.get("type", "")

            if frame_type == "text":
                return AgentEvent(
                    sequence=self._next_seq(),
                    level=EventLevel.STDOUT,
                    content=frame.get("text", ""),
                    timestamp=self._now(),
                    raw_json=frame,
                )
            elif frame_type in ("tool_use", "tool_result"):
                return AgentEvent(
                    sequence=self._next_seq(),
                    level=EventLevel.TOOL_USE,
                    content=json.dumps(frame),
                    timestamp=self._now(),
                    raw_json=frame,
                )
            elif frame_type == "assistant":
                # Extract text content from assistant message if present
                content_blocks = frame.get("message", {}).get("content", [])
                text_parts = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]
                tool_uses = [b for b in content_blocks if b.get("type") == "tool_use"]
                events = []
                for text in text_parts:
                    if text:
                        events.append(AgentEvent(
                            sequence=self._next_seq(),
                            level=EventLevel.STDOUT,
                            content=text,
                            timestamp=self._now(),
                            raw_json=frame,
                        ))
                for tool in tool_uses:
                    events.append(AgentEvent(
                        sequence=self._next_seq(),
                        level=EventLevel.TOOL_USE,
                        content=json.dumps(tool),
                        timestamp=self._now(),
                        raw_json=tool,
                    ))
                # Return first or a combined system event
                if events:
                    return events[0]  # caller iterates; we return one per call
                return AgentEvent(
                    sequence=self._next_seq(),
                    level=EventLevel.SYSTEM,
                    content=line,
                    timestamp=self._now(),
                    raw_json=frame,
                )
            else:
                return AgentEvent(
                    sequence=self._next_seq(),
                    level=EventLevel.SYSTEM,
                    content=line,
                    timestamp=self._now(),
                    raw_json=frame,
                )
        except json.JSONDecodeError:
            return AgentEvent(
                sequence=self._next_seq(),
                level=EventLevel.STDOUT,
                content=line,
                timestamp=self._now(),
                raw_json=None,
            )

    async def _parse_line_multi(self, line: str) -> list[AgentEvent]:
        """Handle assistant messages that can produce multiple events."""
        try:
            frame = json.loads(line)
            if frame.get("type") == "assistant":
                content_blocks = frame.get("message", {}).get("content", [])
                events = []
                for block in content_blocks:
                    btype = block.get("type", "")
                    if btype == "text" and block.get("text"):
                        events.append(AgentEvent(
                            sequence=self._next_seq(),
                            level=EventLevel.STDOUT,
                            content=block["text"],
                            timestamp=self._now(),
                            raw_json=block,
                        ))
                    elif btype == "tool_use":
                        events.append(AgentEvent(
                            sequence=self._next_seq(),
                            level=EventLevel.TOOL_USE,
                            content=json.dumps(block),
                            timestamp=self._now(),
                            raw_json=block,
                        ))
                return events if events else [self._parse_line(line)]
        except json.JSONDecodeError:
            pass
        return [self._parse_line(line)]

    async def run(
        self,
        prompt: str,
        worktree_path: str,
        execution_id: str,
    ) -> AsyncGenerator[AgentEvent, None]:
        yield AgentEvent(
            sequence=self._next_seq(),
            level=EventLevel.SYSTEM,
            content=f"Starting claude in {worktree_path}",
            timestamp=self._now(),
        )

        cmd = self._build_command(prompt)
        env = {**os.environ, "TERM": "dumb", "NO_COLOR": "1"}

        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=worktree_path,
            stdin=asyncio.subprocess.PIPE if not self._skip_permissions else asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        self._pid = self._process.pid

        yield AgentEvent(
            sequence=self._next_seq(),
            level=EventLevel.SYSTEM,
            content=f"Process started with PID {self._pid}",
            timestamp=self._now(),
            raw_json={"pid": self._pid},
        )

        # Drain stderr in background to prevent pipe buffer deadlock
        stderr_task = asyncio.create_task(self._process.stderr.read())

        # Stream stdout line by line
        async for raw_line in self._process.stdout:
            line = raw_line.decode("utf-8", errors="replace").rstrip()
            if not line:
                continue

            # Intercept permission prompts when not auto-approving
            if not self._skip_permissions and _APPROVAL_RE.search(line):
                approval_id = str(uuid.uuid4())
                yield AgentEvent(
                    sequence=self._next_seq(),
                    level=EventLevel.SYSTEM,
                    content=line,
                    timestamp=self._now(),
                    raw_json={"type": "approval_request", "approval_id": approval_id, "prompt_text": line},
                )
                approved = False
                if self._approval_callback:
                    try:
                        approved = await self._approval_callback(
                            self._api_url, execution_id, approval_id, line
                        )
                    except Exception as e:
                        print(f"[claude] Approval callback error: {e}")
                # Write decision to stdin
                if self._process.stdin:
                    response = b"y\n" if approved else b"n\n"
                    self._process.stdin.write(response)
                    await self._process.stdin.drain()
                continue

            for event in await self._parse_line_multi(line):
                yield event

        await self._process.wait()
        exit_code = self._process.returncode

        # Emit any stderr collected
        try:
            stderr_bytes = await asyncio.wait_for(stderr_task, timeout=1.0)
            stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()
            if stderr_text:
                for stderr_line in stderr_text.splitlines():
                    if stderr_line.strip():
                        yield AgentEvent(
                            sequence=self._next_seq(),
                            level=EventLevel.STDERR,
                            content=stderr_line,
                            timestamp=self._now(),
                        )
        except asyncio.TimeoutError:
            pass

        status = AgentStatus.COMPLETED if exit_code == 0 else AgentStatus.FAILED
        yield AgentEvent(
            sequence=self._next_seq(),
            level=EventLevel.SYSTEM,
            content=json.dumps({"type": "process_exit", "exit_code": exit_code, "status": status}),
            timestamp=self._now(),
            raw_json={"type": "process_exit", "exit_code": exit_code, "status": status},
        )

    async def stop(self, execution_id: str) -> bool:
        if self._process and self._process.returncode is None:
            try:
                self._process.send_signal(signal.SIGTERM)
                try:
                    await asyncio.wait_for(self._process.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self._process.kill()
                return True
            except ProcessLookupError:
                return False
        return False
