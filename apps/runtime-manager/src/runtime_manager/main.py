import asyncio
import json
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

import redis.asyncio as aioredis

from .config import settings
from .process_manager import process_manager

QUEUE_KEY = "kanban:run_queue"


async def _queue_worker() -> None:
    """Poll Redis queue and dispatch executions."""
    from .runner import run_execution
    r = aioredis.from_url(settings.redis_url, decode_responses=True)
    print("[queue-worker] started")
    while True:
        try:
            items = await r.zpopmin(QUEUE_KEY, 1)
            if items:
                raw, _score = items[0]
                payload = json.loads(raw)
                asyncio.create_task(run_execution(**payload))
            else:
                await asyncio.sleep(settings.queue_poll_interval)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[queue-worker] error: {e}")
            await asyncio.sleep(1.0)
    await r.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_queue_worker())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="Kanban Runtime Manager", version="0.1.0", lifespan=lifespan)


class RunRequest(BaseModel):
    execution_id: str
    task_id: str
    task_title: str
    task_description: str = ""
    prompt_override: Optional[str] = None
    agent: str = "claude-code"
    model: str = "sonnet"                    # resolved model (e.g. sonnet, opus, haiku)
    max_budget_usd: float = 2.00             # per-execution cost cap
    openai_api_key: str = ""                 # passed through for Codex adapter
    gemini_api_key: str = ""                 # passed through for Gemini adapter
    worktree_path: Optional[str] = None
    branch_name: Optional[str] = None
    repo_path: Optional[str] = None
    project_name: Optional[str] = None
    base_branch: str = "main"
    skip_permissions: bool = True            # False = human approval mode
    skip_worktree_commit: bool = False       # True for validation runs
    skip_context_inject: bool = False        # True for validation runs
    impl_execution_id: Optional[str] = None # Set on validation runs for WS routing
    use_docker: bool = False                 # Run agent inside Docker sandbox
    prior_work: list = []                    # Sprint 5: similar prior context records


class ApprovalSignal(BaseModel):
    approved: bool


@app.post("/run")
async def run(req: RunRequest):
    from .runner import run_execution
    asyncio.create_task(
        run_execution(
            execution_id=req.execution_id,
            task_id=req.task_id,
            task_title=req.task_title,
            task_description=req.task_description,
            worktree_path=req.worktree_path,
            branch_name=req.branch_name,
            repo_path=req.repo_path,
            project_name=req.project_name,
            base_branch=req.base_branch,
            prompt_override=req.prompt_override,
            agent=req.agent,
            model=req.model,
            max_budget_usd=req.max_budget_usd,
            openai_api_key=req.openai_api_key,
            gemini_api_key=req.gemini_api_key,
            skip_permissions=req.skip_permissions,
            skip_worktree_commit=req.skip_worktree_commit,
            skip_context_inject=req.skip_context_inject,
            impl_execution_id=req.impl_execution_id,
            use_docker=req.use_docker,
            prior_work=req.prior_work,
        )
    )
    return {"execution_id": req.execution_id, "status": "started"}


@app.post("/signal/approval/{approval_id}")
async def signal_approval(approval_id: str, body: ApprovalSignal):
    from .approval_registry import resolve
    resolved = resolve(approval_id, body.approved)
    return {"ok": resolved, "approval_id": approval_id}


@app.post("/stop/{execution_id}")
async def stop(execution_id: str):
    ok = await process_manager.stop(execution_id)
    return {"ok": ok, "execution_id": execution_id}


@app.get("/status/{execution_id}")
async def status(execution_id: str):
    pid = process_manager.pid(execution_id)
    return {
        "execution_id": execution_id,
        "active": pid is not None,
        "pid": pid,
    }


@app.get("/health")
async def health():
    return {"status": "ok", "service": "runtime-manager"}
