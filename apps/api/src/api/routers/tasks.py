from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from ..database import get_db
from ..schemas import TaskCreate, TaskUpdate, Task
from ..services import task_service, project_service

router = APIRouter(tags=["tasks"])


@router.get("/api/v1/projects/{project_id}/tasks", response_model=dict)
async def list_tasks(project_id: str, status: Optional[str] = Query(None)):
    async with get_db() as db:
        project = await project_service.get(db, project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        tasks = await task_service.list_for_project(db, project_id, status)
    return {"tasks": [t.model_dump() for t in tasks]}


@router.post("/api/v1/projects/{project_id}/tasks", response_model=Task, status_code=201)
async def create_task(project_id: str, data: TaskCreate):
    async with get_db() as db:
        project = await project_service.get(db, project_id)
        if not project:
            raise HTTPException(404, "Project not found")
        return await task_service.create(db, project_id, data)


@router.get("/api/v1/tasks/{task_id}", response_model=Task)
async def get_task(task_id: str):
    async with get_db() as db:
        task = await task_service.get(db, task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.patch("/api/v1/tasks/{task_id}", response_model=Task)
async def update_task(task_id: str, data: TaskUpdate):
    async with get_db() as db:
        try:
            task = await task_service.update(db, task_id, data)
        except ValueError as e:
            raise HTTPException(400, str(e))
    if not task:
        raise HTTPException(404, "Task not found")
    return task


@router.delete("/api/v1/tasks/{task_id}")
async def delete_task(task_id: str):
    async with get_db() as db:
        ok = await task_service.delete(db, task_id)
    if not ok:
        raise HTTPException(404, "Task not found")
    return {"ok": True}
