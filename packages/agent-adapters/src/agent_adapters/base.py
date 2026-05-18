from __future__ import annotations
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional
from .types import AgentEvent


class AgentAdapter(ABC):
    @abstractmethod
    async def run(
        self,
        prompt: str,
        worktree_path: str,
        execution_id: str,
    ) -> AsyncGenerator[AgentEvent, None]:
        """Yields AgentEvents until the process ends."""
        ...

    @abstractmethod
    async def stop(self, execution_id: str) -> bool:
        """Sends SIGTERM. Returns True if process was alive."""
        ...

    @property
    @abstractmethod
    def pid(self) -> Optional[int]:
        ...
