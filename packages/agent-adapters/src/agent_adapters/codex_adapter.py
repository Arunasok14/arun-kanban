from __future__ import annotations
import asyncio
import json
import os
import signal
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from .base import AgentAdapter
from .types import AgentEvent, AgentStatus, EventLevel

CODEX_BIN = os.environ.get("CODEX_BIN", "codex")


class CodexAdapter(AgentAdapter):
    """
    Adapter for OpenAI Codex CLI.
    Requires: `npm install -g @openai/codex` and OPENAI_API_KEY set.
    Status: Phase 2 — stub implementation.
    """

    def __init__(self, api_key: str = "", model: str = "codex"):
        self._api_key = api_key
        self._model = model
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

    async def run(
        self,
        prompt: str,
        worktree_path: str,
        execution_id: str,
    ) -> AsyncGenerator[AgentEvent, None]:
        if not self._api_key:
            yield AgentEvent(
                sequence=self._next_seq(),
                level=EventLevel.SYSTEM,
                content="ERROR: OpenAI API key not configured. Go to Settings → API Keys.",
                timestamp=self._now(),
            )
            return

        yield AgentEvent(
            sequence=self._next_seq(),
            level=EventLevel.SYSTEM,
            content=f"Starting Codex CLI in {worktree_path}",
            timestamp=self._now(),
        )

        env = {**os.environ, "OPENAI_API_KEY": self._api_key, "NO_COLOR": "1"}
        cmd = [CODEX_BIN, "--approval-mode", "full-auto", "--quiet", prompt]

        try:
            self._process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=worktree_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            self._pid = self._process.pid

            yield AgentEvent(
                sequence=self._next_seq(),
                level=EventLevel.SYSTEM,
                content=f"Codex process started with PID {self._pid}",
                timestamp=self._now(),
                raw_json={"pid": self._pid},
            )

            # Drain stderr concurrently to prevent pipe buffer deadlock
            stderr_task = asyncio.create_task(self._process.stderr.read())

            async for raw_line in self._process.stdout:
                line = raw_line.decode("utf-8", errors="replace").rstrip()
                if line:
                    yield AgentEvent(
                        sequence=self._next_seq(),
                        level=EventLevel.STDOUT,
                        content=line,
                        timestamp=self._now(),
                    )

            await self._process.wait()
            exit_code = self._process.returncode
            status = AgentStatus.COMPLETED if exit_code == 0 else AgentStatus.FAILED

            # Emit stderr if any
            try:
                stderr_bytes = await asyncio.wait_for(stderr_task, timeout=1.0)
                stderr_text = stderr_bytes.decode("utf-8", errors="replace").strip()
                if stderr_text:
                    for line in stderr_text.splitlines():
                        if line.strip():
                            yield AgentEvent(
                                sequence=self._next_seq(),
                                level=EventLevel.STDERR,
                                content=line,
                                timestamp=self._now(),
                            )
            except asyncio.TimeoutError:
                pass

            yield AgentEvent(
                sequence=self._next_seq(),
                level=EventLevel.SYSTEM,
                content=json.dumps({"type": "process_exit", "exit_code": exit_code, "status": status}),
                timestamp=self._now(),
                raw_json={"type": "process_exit", "exit_code": exit_code, "status": status},
            )

        except FileNotFoundError:
            yield AgentEvent(
                sequence=self._next_seq(),
                level=EventLevel.SYSTEM,
                content=f"ERROR: Codex CLI not found at '{CODEX_BIN}'. Install with: npm install -g @openai/codex",
                timestamp=self._now(),
                raw_json={"type": "process_exit", "exit_code": 1, "status": AgentStatus.FAILED},
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
