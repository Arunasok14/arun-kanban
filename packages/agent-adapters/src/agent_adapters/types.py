from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class EventLevel(str, Enum):
    STDOUT = "stdout"
    STDERR = "stderr"
    SYSTEM = "system"
    TOOL_USE = "tool_use"


@dataclass
class AgentEvent:
    sequence: int
    level: EventLevel
    content: str
    timestamp: str
    raw_json: Optional[dict] = field(default=None)
