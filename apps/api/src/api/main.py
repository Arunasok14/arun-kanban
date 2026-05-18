from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db
from .routers import projects, tasks, executions, websocket, settings, approvals, policies


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Kanban AI Orchestrator API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(tasks.router)
app.include_router(executions.router)
app.include_router(executions.internal_router)
app.include_router(websocket.router)
app.include_router(settings.router)
app.include_router(approvals.router)
app.include_router(approvals.internal_router)
app.include_router(policies.router)
app.include_router(policies.internal_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "kanban-api"}
