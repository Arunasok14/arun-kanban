from __future__ import annotations
import aiosqlite
from typing import Optional
from ..schemas import ProjectCreate, ProjectUpdate, Project, new_id, utcnow


async def create(db: aiosqlite.Connection, data: ProjectCreate) -> Project:
    pid = new_id()
    now = utcnow()
    await db.execute(
        """INSERT INTO projects (id, name, description, repo_path, default_branch, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (pid, data.name, data.description, data.repo_path, data.default_branch, now, now),
    )
    await db.commit()
    return await get(db, pid)


async def get(db: aiosqlite.Connection, project_id: str) -> Optional[Project]:
    async with db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)) as cur:
        row = await cur.fetchone()
    if not row:
        return None
    return Project(**dict(row))


async def list_all(db: aiosqlite.Connection) -> list[Project]:
    async with db.execute("SELECT * FROM projects ORDER BY created_at DESC") as cur:
        rows = await cur.fetchall()
    return [Project(**dict(r)) for r in rows]


async def update(db: aiosqlite.Connection, project_id: str, data: ProjectUpdate) -> Optional[Project]:
    fields = data.model_dump(exclude_none=True)
    if not fields:
        return await get(db, project_id)
    fields["updated_at"] = utcnow()
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [project_id]
    await db.execute(f"UPDATE projects SET {set_clause} WHERE id = ?", values)
    await db.commit()
    return await get(db, project_id)


async def delete(db: aiosqlite.Connection, project_id: str) -> bool:
    cur = await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    await db.commit()
    return cur.rowcount > 0
