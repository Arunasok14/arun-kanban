"""
In-process approval registry.

When the Claude adapter detects a permission prompt, it calls
`request_approval()` which:
  1. Evaluates the prompt against the policy engine (Sprint 6)
     - deny  → return False immediately, no Future created
     - warn  → escalate to human; continues to step 2
     - allow → continues to step 2 (normal flow without approval popup)
  2. Creates an asyncio.Future keyed by approval_id
  3. POSTs to the API so the UI is notified via WebSocket
  4. Awaits the Future (with a 5-minute timeout → auto-deny)

When the operator decides in the UI, the API:
  1. Updates the DB
  2. POSTs to /signal/approval/{id} on the runtime-manager
  3. `resolve()` sets the Future result → adapter writes y/n to stdin
"""
from __future__ import annotations
import asyncio
from typing import Optional
import httpx

from .policy_engine import evaluate as policy_evaluate, DEFAULT_POLICIES

_pending: dict[str, asyncio.Future] = {}


async def _fetch_user_policies(api_url: str) -> list[dict]:
    """Fetch user-defined policies from the API (best-effort)."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{api_url}/api/internal/policies")
            if r.status_code == 200:
                return r.json().get("policies", [])
    except Exception:
        pass
    return []


async def _post_policy_denial(
    api_url: str,
    execution_id: str,
    approval_id: str,
    prompt_text: str,
    message: str,
) -> None:
    """Notify API that a policy denied this request (creates a system log event)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{api_url}/api/internal/executions/{execution_id}/approval_request",
                json={
                    "approval_id": approval_id,
                    "prompt_text": prompt_text,
                    "policy_denied": True,
                    "policy_message": message,
                },
            )
    except Exception:
        pass


async def request_approval(
    api_url: str,
    execution_id: str,
    approval_id: str,
    prompt_text: str,
    timeout: float = 300.0,
) -> bool:
    """Register an approval request and block until decided or timeout."""

    # ── Sprint 6: Policy evaluation ───────────────────────────────────────────
    user_policies = await _fetch_user_policies(api_url)
    result = policy_evaluate(prompt_text, extra_policies=user_policies)

    if result.action == "deny":
        print(f"[policy] DENIED by policy '{result.policy_id}': {result.message}")
        await _post_policy_denial(api_url, execution_id, approval_id, prompt_text, result.message)
        return False  # immediately deny — caller writes "n\n" to stdin

    if result.action == "allow":
        # No approval needed — auto-approve (skip_permissions was already False
        # meaning the adapter is asking us, but policy says it's fine)
        return True

    # action == "warn" → fall through to human approval
    # ─────────────────────────────────────────────────────────────────────────

    loop = asyncio.get_event_loop()
    fut: asyncio.Future = loop.create_future()
    _pending[approval_id] = fut

    # Notify API so it persists the request and fans out via WebSocket
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{api_url}/api/internal/executions/{execution_id}/approval_request",
                json={"approval_id": approval_id, "prompt_text": prompt_text},
            )
    except Exception as e:
        print(f"[approval] Failed to notify API of approval request {approval_id}: {e}")
        _pending.pop(approval_id, None)
        return False  # safe default: deny

    try:
        return await asyncio.wait_for(fut, timeout=timeout)
    except asyncio.TimeoutError:
        _pending.pop(approval_id, None)
        # Notify API of timeout
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{api_url}/api/internal/executions/{execution_id}/approval_request",
                    json={"approval_id": approval_id, "prompt_text": prompt_text, "timed_out": True},
                )
        except Exception:
            pass
        return False  # auto-deny on timeout


def resolve(approval_id: str, approved: bool) -> bool:
    """Called by the signal endpoint when operator decides."""
    fut = _pending.pop(approval_id, None)
    if fut is None or fut.done():
        return False
    fut.set_result(approved)
    return True
