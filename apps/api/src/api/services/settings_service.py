from __future__ import annotations
import aiosqlite
from ..schemas import SettingsRead, SettingsUpdate, utcnow


async def _get_raw(db: aiosqlite.Connection) -> dict[str, str]:
    async with db.execute("SELECT key, value FROM settings") as cur:
        rows = await cur.fetchall()
    return {row["key"]: row["value"] for row in rows}


async def get(db: aiosqlite.Connection) -> SettingsRead:
    raw = await _get_raw(db)
    return SettingsRead(
        default_model=raw.get("default_model", "sonnet"),
        default_agent=raw.get("default_agent", "claude-code"),
        default_budget_usd=raw.get("default_budget_usd", "2.00"),
        openai_api_key_set=bool(raw.get("openai_api_key", "").strip()),
        gemini_api_key_set=bool(raw.get("gemini_api_key", "").strip()),
        require_approval=raw.get("require_approval", "false").lower() == "true",
        github_token_set=bool(raw.get("github_token", "").strip()),
        github_repo=raw.get("github_repo", ""),
        vercel_token_set=bool(raw.get("vercel_token", "").strip()),
        vercel_project_id=raw.get("vercel_project_id", ""),
        auto_deploy=raw.get("auto_deploy", "false").lower() == "true",
        docker_sandbox=raw.get("docker_sandbox", "false").lower() == "true",
        stage_model_plan=raw.get("stage_model_plan", "opus"),
        stage_model_in_progress=raw.get("stage_model_in_progress", "sonnet"),
        stage_model_testing=raw.get("stage_model_testing", "haiku"),
    )


async def get_value(db: aiosqlite.Connection, key: str, default: str = "") -> str:
    async with db.execute("SELECT value FROM settings WHERE key = ?", (key,)) as cur:
        row = await cur.fetchone()
    return row["value"] if row else default


async def update(db: aiosqlite.Connection, data: SettingsUpdate) -> SettingsRead:
    now = utcnow()
    pairs: dict[str, str] = {}

    if data.default_model is not None:
        pairs["default_model"] = data.default_model
    if data.default_agent is not None:
        pairs["default_agent"] = data.default_agent
    if data.default_budget_usd is not None:
        pairs["default_budget_usd"] = data.default_budget_usd
    if data.openai_api_key is not None:
        pairs["openai_api_key"] = data.openai_api_key
    if data.gemini_api_key is not None:
        pairs["gemini_api_key"] = data.gemini_api_key
    if data.require_approval is not None:
        pairs["require_approval"] = "true" if data.require_approval else "false"
    if data.github_token is not None:
        pairs["github_token"] = data.github_token
    if data.github_repo is not None:
        pairs["github_repo"] = data.github_repo
    if data.vercel_token is not None:
        pairs["vercel_token"] = data.vercel_token
    if data.vercel_project_id is not None:
        pairs["vercel_project_id"] = data.vercel_project_id
    if data.auto_deploy is not None:
        pairs["auto_deploy"] = "true" if data.auto_deploy else "false"
    if data.docker_sandbox is not None:
        pairs["docker_sandbox"] = "true" if data.docker_sandbox else "false"
    if data.stage_model_plan is not None:
        pairs["stage_model_plan"] = data.stage_model_plan
    if data.stage_model_in_progress is not None:
        pairs["stage_model_in_progress"] = data.stage_model_in_progress
    if data.stage_model_testing is not None:
        pairs["stage_model_testing"] = data.stage_model_testing

    for key, value in pairs.items():
        await db.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, value, now),
        )
    await db.commit()
    return await get(db)
