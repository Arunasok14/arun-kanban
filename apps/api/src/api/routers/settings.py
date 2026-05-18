from fastapi import APIRouter
from ..database import get_db
from ..schemas import SettingsRead, SettingsUpdate, AVAILABLE_MODELS, AVAILABLE_AGENTS
from ..services import settings_service

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("", response_model=SettingsRead)
async def get_settings():
    async with get_db() as db:
        return await settings_service.get(db)


@router.patch("", response_model=SettingsRead)
async def update_settings(data: SettingsUpdate):
    async with get_db() as db:
        return await settings_service.update(db, data)


@router.get("/models")
async def list_models():
    return {"models": AVAILABLE_MODELS}


@router.get("/agents")
async def list_agents():
    return {"agents": AVAILABLE_AGENTS}
