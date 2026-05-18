from __future__ import annotations
import json
import aiosqlite
from typing import Optional
from ..schemas import (
    Execution, LogEntry, InternalEventCreate, InternalStatusUpdate, InternalTokenUpdate,
    new_id, utcnow
)


async def create(
    db: aiosqlite.Connection,
    task_id: str,
    agent: str = "claude-code",
    execution_type: str = "implementation",
) -> Execution:
    eid = new_id()
    now = utcnow()
    await db.execute(
        """INSERT INTO executions (id, task_id, status, agent, execution_type, created_at)
           VALUES (?, ?, 'pending', ?, ?, ?)""",
        (eid, task_id, agent, execution_type, now),
    )
    await db.commit()
    return await get(db, eid)


async def get(db: aiosqlite.Connection, execution_id: str) -> Optional[Execution]:
    async with db.execute("SELECT * FROM executions WHERE id = ?", (execution_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        return None
    d = dict(row)
    if d.get("token_usage") and isinstance(d["token_usage"], str):
        try:
            d["token_usage"] = json.loads(d["token_usage"])
        except Exception:
            pass
    # SQLite stores booleans as integers
    d["budget_exhausted"] = bool(d.get("budget_exhausted", 0))
    return Execution(**d)


async def list_for_task(db: aiosqlite.Connection, task_id: str) -> list[Execution]:
    async with db.execute(
        "SELECT * FROM executions WHERE task_id = ? ORDER BY created_at DESC", (task_id,)
    ) as cur:
        rows = await cur.fetchall()
    result = []
    for row in rows:
        d = dict(row)
        if d.get("token_usage") and isinstance(d["token_usage"], str):
            try:
                d["token_usage"] = json.loads(d["token_usage"])
            except Exception:
                pass
        result.append(Execution(**d))
    return result


async def apply_event(
    db: aiosqlite.Connection, execution_id: str, event: InternalEventCreate
) -> LogEntry:
    await db.execute(
        """INSERT INTO execution_logs (execution_id, sequence, level, content, timestamp)
           VALUES (?, ?, ?, ?, ?)""",
        (execution_id, event.sequence, event.level, event.content, event.timestamp),
    )
    await db.commit()
    async with db.execute(
        "SELECT * FROM execution_logs WHERE execution_id = ? AND sequence = ?",
        (execution_id, event.sequence),
    ) as cur:
        row = await cur.fetchone()
    return LogEntry(**dict(row))


async def update_token_usage(
    db: aiosqlite.Connection, execution_id: str, update: InternalTokenUpdate
) -> Execution:
    """Accumulate token counts and cost; flag budget_exhausted."""
    await db.execute(
        """UPDATE executions SET
             token_input = COALESCE(token_input, 0) + ?,
             token_output = COALESCE(token_output, 0) + ?,
             cost_usd = COALESCE(cost_usd, 0.0) + ?,
             budget_exhausted = ?
           WHERE id = ?""",
        (update.input_tokens, update.output_tokens, update.cost_usd,
         1 if update.budget_exhausted else 0, execution_id),
    )
    await db.commit()
    return await get(db, execution_id)


async def apply_status(
    db: aiosqlite.Connection, execution_id: str, update: InternalStatusUpdate
) -> Execution:
    fields: dict = {"status": update.status, "updated_at": utcnow()}
    if update.pid is not None:
        fields["pid"] = update.pid
    if update.exit_code is not None:
        fields["exit_code"] = update.exit_code
    if update.token_usage is not None:
        fields["token_usage"] = json.dumps(update.token_usage)
    if update.error_message is not None:
        fields["error_message"] = update.error_message
    if update.started_at is not None:
        fields["started_at"] = update.started_at
    if update.finished_at is not None:
        fields["finished_at"] = update.finished_at
    if update.budget_usd is not None:
        fields["budget_usd"] = update.budget_usd

    fields.pop("updated_at", None)  # executions table has no updated_at

    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [execution_id]
    await db.execute(f"UPDATE executions SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return await get(db, execution_id)


async def get_logs(
    db: aiosqlite.Connection, execution_id: str, after_sequence: int = 0
) -> list[LogEntry]:
    async with db.execute(
        """SELECT * FROM execution_logs WHERE execution_id = ? AND sequence > ?
           ORDER BY sequence ASC""",
        (execution_id, after_sequence),
    ) as cur:
        rows = await cur.fetchall()
    return [LogEntry(**dict(r)) for r in rows]
