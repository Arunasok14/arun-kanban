import asyncio
from collections import defaultdict
from typing import Dict, Set


class EventBus:
    def __init__(self):
        self._subscribers: Dict[str, Set[asyncio.Queue]] = defaultdict(set)

    def subscribe(self, execution_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers[execution_id].add(q)
        return q

    def unsubscribe(self, execution_id: str, q: asyncio.Queue) -> None:
        self._subscribers[execution_id].discard(q)
        if not self._subscribers.get(execution_id):
            self._subscribers.pop(execution_id, None)

    async def publish(self, execution_id: str, event: dict) -> None:
        for q in list(self._subscribers.get(execution_id, set())):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass  # slow subscriber — drop; they can catch up via DB

    async def publish_done(self, execution_id: str) -> None:
        await self.publish(execution_id, {"type": "__done__"})


event_bus = EventBus()
