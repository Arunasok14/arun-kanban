"""
Policy CRUD endpoints (Sprint 6).

Public API (/api/v1/policies):
  GET    /api/v1/policies            — list all policies
  POST   /api/v1/policies            — create a user-defined policy
  PATCH  /api/v1/policies/{id}       — update (toggle, edit)
  DELETE /api/v1/policies/{id}       — remove

Internal API (called by runtime-manager):
  GET    /api/internal/policies      — list enabled policies (runtime-manager fetches at eval time)
"""
from __future__ import annotations
from fastapi import APIRouter, HTTPException
from ..database import get_db
from ..schemas import Policy, PolicyCreate, PolicyUpdate, new_id, utcnow

router = APIRouter(tags=["policies"])
internal_router = APIRouter(prefix="/api/internal", tags=["internal"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _row_to_policy(row) -> Policy:
    d = dict(row)
    d["enabled"] = bool(d["enabled"])
    return Policy(**d)


# ── Public endpoints ───────────────────────────────────────────────────────────

@router.get("/api/v1/policies", response_model=dict)
async def list_policies():
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM policies ORDER BY created_at ASC"
        ) as cur:
            rows = await cur.fetchall()
    return {"policies": [_row_to_policy(r).model_dump() for r in rows]}


@router.post("/api/v1/policies", response_model=Policy, status_code=201)
async def create_policy(data: PolicyCreate):
    pid = new_id()
    now = utcnow()
    async with get_db() as db:
        await db.execute(
            """INSERT INTO policies (id, pattern, action, message, enabled, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (pid, data.pattern, data.action, data.message, int(data.enabled), now, now),
        )
        await db.commit()
        async with db.execute("SELECT * FROM policies WHERE id = ?", (pid,)) as cur:
            row = await cur.fetchone()
    return _row_to_policy(row)


@router.patch("/api/v1/policies/{policy_id}", response_model=Policy)
async def update_policy(policy_id: str, data: PolicyUpdate):
    async with get_db() as db:
        async with db.execute("SELECT * FROM policies WHERE id = ?", (policy_id,)) as cur:
            existing = await cur.fetchone()
        if not existing:
            raise HTTPException(404, "Policy not found")

        fields = data.model_dump(exclude_none=True)
        if not fields:
            return _row_to_policy(existing)

        if "enabled" in fields:
            fields["enabled"] = int(fields["enabled"])
        fields["updated_at"] = utcnow()
        set_clause = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [policy_id]
        await db.execute(f"UPDATE policies SET {set_clause} WHERE id = ?", values)
        await db.commit()
        async with db.execute("SELECT * FROM policies WHERE id = ?", (policy_id,)) as cur:
            row = await cur.fetchone()
    return _row_to_policy(row)


@router.delete("/api/v1/policies/{policy_id}")
async def delete_policy(policy_id: str):
    async with get_db() as db:
        cur = await db.execute("DELETE FROM policies WHERE id = ?", (policy_id,))
        await db.commit()
    if cur.rowcount == 0:
        raise HTTPException(404, "Policy not found")
    return {"ok": True}


# ── Internal endpoint (runtime-manager fetches at eval time) ──────────────────

@internal_router.get("/policies")
async def internal_list_policies():
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM policies WHERE enabled = 1 ORDER BY created_at ASC"
        ) as cur:
            rows = await cur.fetchall()
    return {"policies": [_row_to_policy(r).model_dump() for r in rows]}
