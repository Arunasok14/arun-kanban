from fastapi import APIRouter, HTTPException
from ..database import get_db
from ..schemas import ProjectCreate, ProjectUpdate, Project
from ..services import project_service

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


@router.get("", response_model=dict)
async def list_projects():
    async with get_db() as db:
        projects = await project_service.list_all(db)
    return {"projects": [p.model_dump() for p in projects]}


@router.post("", response_model=Project, status_code=201)
async def create_project(data: ProjectCreate):
    async with get_db() as db:
        return await project_service.create(db, data)


@router.get("/{project_id}", response_model=Project)
async def get_project(project_id: str):
    async with get_db() as db:
        project = await project_service.get(db, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.patch("/{project_id}", response_model=Project)
async def update_project(project_id: str, data: ProjectUpdate):
    async with get_db() as db:
        project = await project_service.update(db, project_id, data)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    async with get_db() as db:
        ok = await project_service.delete(db, project_id)
    if not ok:
        raise HTTPException(404, "Project not found")
    return {"ok": True}
