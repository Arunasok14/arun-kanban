"""
Vercel deployment integration (Sprint 7).

Triggers a preview deployment for a branch and polls until ready.
Uses Vercel's REST API v13.
"""
from __future__ import annotations
import asyncio
import httpx
from typing import Optional


async def trigger_deploy(
    project_id: str,
    branch: str,
    token: str,
    team_id: Optional[str] = None,
) -> str:
    """
    Create a Vercel deployment for *branch*. Returns the deployment ID.
    Raises on API failure.
    """
    params: dict = {}
    if team_id:
        params["teamId"] = team_id

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(
            "https://api.vercel.com/v13/deployments",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            params=params,
            json={
                "name": project_id,
                "gitSource": {
                    "type": "github",
                    "ref": branch,
                },
                "target": "preview",
            },
        )
        r.raise_for_status()
        return r.json()["id"]


async def poll_until_ready(
    deployment_id: str,
    token: str,
    team_id: Optional[str] = None,
    timeout: float = 300.0,
    poll_interval: float = 5.0,
) -> Optional[str]:
    """
    Poll the Vercel API until deployment *deployment_id* reaches READY state.
    Returns the preview URL or None on timeout/error.
    """
    params: dict = {}
    if team_id:
        params["teamId"] = team_id

    deadline = asyncio.get_event_loop().time() + timeout

    async with httpx.AsyncClient(timeout=10.0) as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                r = await client.get(
                    f"https://api.vercel.com/v13/deployments/{deployment_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    params=params,
                )
                if r.is_success:
                    data = r.json()
                    state = data.get("readyState") or data.get("state", "")
                    if state == "READY":
                        url = data.get("url")
                        return f"https://{url}" if url and not url.startswith("https://") else url
                    if state in ("ERROR", "CANCELED"):
                        print(f"[vercel] Deployment {deployment_id} ended in state {state}")
                        return None
            except Exception as e:
                print(f"[vercel] Poll error: {e}")

            await asyncio.sleep(poll_interval)

    print(f"[vercel] Timed out waiting for deployment {deployment_id}")
    return None
