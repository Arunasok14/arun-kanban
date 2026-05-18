from __future__ import annotations
from typing import Dict, Optional
from agent_adapters.base import AgentAdapter


class ProcessManager:
    """Registry of active AgentAdapter instances keyed by execution_id."""

    def __init__(self):
        self._adapters: Dict[str, AgentAdapter] = {}

    def register(self, execution_id: str, adapter: AgentAdapter) -> None:
        self._adapters[execution_id] = adapter

    def get(self, execution_id: str) -> Optional[AgentAdapter]:
        return self._adapters.get(execution_id)

    def unregister(self, execution_id: str) -> None:
        self._adapters.pop(execution_id, None)

    async def stop(self, execution_id: str) -> bool:
        adapter = self._adapters.get(execution_id)
        if adapter:
            return await adapter.stop(execution_id)
        return False

    def pid(self, execution_id: str) -> Optional[int]:
        adapter = self._adapters.get(execution_id)
        return adapter.pid if adapter else None


process_manager = ProcessManager()
