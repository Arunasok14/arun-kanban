"""
Redis-backed task queue for dispatching executions to the runtime-manager.

Uses a Redis sorted set (score = enqueue timestamp) so executions are
processed in FIFO order. The runtime-manager polls and pops work items.
"""
from __future__ import annotations
import json
import time
from typing import Optional

import redis.asyncio as aioredis

from .config import settings

QUEUE_KEY = "kanban:run_queue"

_redis: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def enqueue(payload: dict) -> None:
    """Push a run payload onto the queue (score = current timestamp → FIFO)."""
    r = get_redis()
    await r.zadd(QUEUE_KEY, {json.dumps(payload): time.time()})


async def dequeue() -> Optional[dict]:
    """Pop the oldest item from the queue, or None if empty."""
    r = get_redis()
    items = await r.zpopmin(QUEUE_KEY, 1)
    if not items:
        return None
    raw, _score = items[0]
    return json.loads(raw)


async def close() -> None:
    global _redis
    if _redis:
        await _redis.aclose()
        _redis = None
