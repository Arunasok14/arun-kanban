from __future__ import annotations
import json
import aiosqlite
from typing import Optional
from ..schemas import (
    TaskCreate, TaskUpdate, Task, ExecutionSummary,
    VALID_STATUSES, new_id, utcnow
)


async def _row_to_task(db: aiosqlite.Connection, row: aiosqlite.Row) -> Task:
    d = dict(row)
    # Deserialise test_results JSON
    if d.get("test_results") and isinstance(d["test_results"], str):
        try:
            d["test_results"] = json.loads(d["test_results"])
        except Exception:
            d["test_results"] = None
    # Phase 3: ensure plan_revision is an int (migration sets DEFAULT 0 but may be None in old rows)
    if d.get("plan_revision") is None:
        d["plan_revision"] = 0
    # Attach latest implementation execution summary (skip validation executions)
    async with db.execute(
        """SELECT id, status, started_at FROM executions
           WHERE task_id = ? AND execution_type = 'implementation'
           ORDER BY created_at DESC LIMIT 1""",
        (d["id"],),
    ) as cur:
        exec_row = await cur.fetchone()
    latest = ExecutionSummary(**dict(exec_row)) if exec_row else None
    return Task(**d, latest_execution=latest)


async def create(db: aiosqlite.Connection, project_id: str, data: TaskCreate) -> Task:
    tid = new_id()
    now = utcnow()
    # Position = max existing + 1 in backlog
    async with db.execute(
        "SELECT COALESCE(MAX(position), -1) FROM tasks WHERE project_id = ? AND status = 'backlog'",
        (project_id,),
    ) as cur:
        row = await cur.fetchone()
    position = (row[0] or 0) + 1
    await db.execute(
        """INSERT INTO tasks (id, project_id, title, description, status, agent, position, created_at, updated_at)
           VALUES (?, ?, ?, ?, 'backlog', ?, ?, ?, ?)""",
        (tid, project_id, data.title, data.description, data.agent, position, now, now),
    )
    await db.commit()
    return await get(db, tid)


async def get(db: aiosqlite.Connection, task_id: str) -> Optional[Task]:
    async with db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        return None
    return await _row_to_task(db, row)


async def list_for_project(
    db: aiosqlite.Connection, project_id: str, status: Optional[str] = None
) -> list[Task]:
    if status:
        async with db.execute(
            "SELECT * FROM tasks WHERE project_id = ? AND status = ? ORDER BY position ASC",
            (project_id, status),
        ) as cur:
            rows = await cur.fetchall()
    else:
        async with db.execute(
            "SELECT * FROM tasks WHERE project_id = ? ORDER BY status, position ASC",
            (project_id,),
        ) as cur:
            rows = await cur.fetchall()
    return [await _row_to_task(db, r) for r in rows]


async def update(db: aiosqlite.Connection, task_id: str, data: TaskUpdate) -> Optional[Task]:
    fields = data.model_dump(exclude_none=True)
    if "status" in fields and fields["status"] not in VALID_STATUSES:
        raise ValueError(f"Invalid status: {fields['status']}")
    # plan_revision: explicit None means "don't change", 0 is valid value so keep it
    if "plan_revision" in fields and fields["plan_revision"] is None:
        del fields["plan_revision"]
    if not fields:
        return await get(db, task_id)
    fields["updated_at"] = utcnow()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [task_id]
    await db.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return await get(db, task_id)


async def set_worktree(
    db: aiosqlite.Connection, task_id: str, worktree_path: str, branch_name: str
) -> None:
    now = utcnow()
    await db.execute(
        "UPDATE tasks SET worktree_path = ?, branch_name = ?, updated_at = ? WHERE id = ?",
        (worktree_path, branch_name, now, task_id),
    )
    await db.commit()


async def set_pr_url(
    db: aiosqlite.Connection, task_id: str, pr_url: str
) -> None:
    now = utcnow()
    await db.execute(
        "UPDATE tasks SET pr_url = ?, updated_at = ? WHERE id = ?",
        (pr_url, now, task_id),
    )
    await db.commit()


async def set_preview_url(
    db: aiosqlite.Connection, task_id: str, preview_url: str
) -> None:
    now = utcnow()
    await db.execute(
        "UPDATE tasks SET preview_url = ?, updated_at = ? WHERE id = ?",
        (preview_url, now, task_id),
    )
    await db.commit()


async def set_test_results(
    db: aiosqlite.Connection, task_id: str, results: dict
) -> None:
    now = utcnow()
    await db.execute(
        "UPDATE tasks SET test_results = ?, updated_at = ? WHERE id = ?",
        (json.dumps(results), now, task_id),
    )
    await db.commit()


async def delete(db: aiosqlite.Connection, task_id: str) -> bool:
    cur = await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    await db.commit()
    return cur.rowcount > 0
