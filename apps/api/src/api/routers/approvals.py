"""
Approval workflow router.

Public endpoints:
  GET  /api/v1/executions/{id}/approvals       — list pending approvals
  POST /api/v1/approvals/{approval_id}/decide  — operator decides y/n

Internal endpoints (called by runtime-manager):
  POST /api/internal/executions/{id}/approval_request — register + broadcast
"""
from __future__ import annotations
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

from ..database import get_db
from ..bus import event_bus
from ..config import settings

router = APIRouter(tags=["approvals"])
internal_router = APIRouter(prefix="/api/internal", tags=["internal"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Schemas ───────────────────────────────────────────────────────────────────

class ApprovalRequestCreate(BaseModel):
    approval_id: str
    prompt_text: str
    timed_out: bool = False


class ApprovalDecide(BaseModel):
    approved: bool


# ── Internal: runtime-manager registers an approval request ──────────────────

@internal_router.post("/executions/{execution_id}/approval_request")
async def create_approval_request(execution_id: str, data: ApprovalRequestCreate):
    now = _now()
    async with get_db() as db:
        if data.timed_out:
            # Update existing record to timeout status
            await db.execute(
                "UPDATE approval_requests SET status = 'timeout', decided_at = ? WHERE id = ?",
                (now, data.approval_id),
            )
        else:
            await db.execute(
                """INSERT OR IGNORE INTO approval_requests
                   (id, execution_id, prompt_text, status, created_at)
                   VALUES (?, ?, ?, 'pending', ?)""",
                (data.approval_id, execution_id, data.prompt_text, now),
            )
        await db.commit()

    frame_type = "approval_timeout" if data.timed_out else "approval_request"
    await event_bus.publish(execution_id, {
        "type": frame_type,
        "approval_id": data.approval_id,
        "prompt_text": data.prompt_text,
    })
    return {"ok": True}


# ── Public: list pending approvals for an execution ──────────────────────────

@router.get("/api/v1/executions/{execution_id}/approvals")
async def list_approvals(execution_id: str):
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM approval_requests WHERE execution_id = ? ORDER BY created_at",
            (execution_id,),
        ) as cur:
            rows = await cur.fetchall()
    return {"approvals": [dict(r) for r in rows]}


# ── Public: operator decides ──────────────────────────────────────────────────

@router.post("/api/v1/approvals/{approval_id}/decide")
async def decide_approval(approval_id: str, data: ApprovalDecide):
    now = _now()
    async with get_db() as db:
        async with db.execute(
            "SELECT * FROM approval_requests WHERE id = ?", (approval_id,)
        ) as cur:
            row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Approval request not found")
        if dict(row)["status"] != "pending":
            raise HTTPException(400, f"Approval already {dict(row)['status']}")

        new_status = "approved" if data.approved else "denied"
        await db.execute(
            "UPDATE approval_requests SET status = ?, decided_at = ? WHERE id = ?",
            (new_status, now, approval_id),
        )
        execution_id = dict(row)["execution_id"]
        await db.commit()

    # Signal the runtime-manager to resolve the Future
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{settings.runtime_manager_url}/signal/approval/{approval_id}",
                json={"approved": data.approved},
            )
    except Exception as e:
        raise HTTPException(503, f"Runtime manager unavailable: {e}")

    # Broadcast decision over WebSocket so UI can dismiss the panel
    await event_bus.publish(execution_id, {
        "type": "approval_decided",
        "approval_id": approval_id,
        "approved": data.approved,
    })

    return {"ok": True, "approved": data.approved}
