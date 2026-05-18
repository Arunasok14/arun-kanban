from __future__ import annotations
from typing import Optional, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import uuid


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# ── Projects ──────────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    repo_path: str
    default_branch: str = "main"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_branch: Optional[str] = None


class Project(BaseModel):
    id: str
    name: str
    description: Optional[str]
    repo_path: str
    default_branch: str
    created_at: str
    updated_at: str


# ── Tasks ─────────────────────────────────────────────────────────────────────

VALID_STATUSES = {"backlog", "plan", "in_progress", "testing", "done"}


class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    agent: str = "claude-code"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    position: Optional[int] = None
    plan_content: Optional[str] = None
    plan_approved_at: Optional[str] = None
    plan_revision: Optional[int] = None


class ExecutionSummary(BaseModel):
    id: str
    status: str
    started_at: Optional[str]


class TestResults(BaseModel):
    passed: int = 0
    failed: int = 0
    errors: int = 0
    details: list[str] = []


class Task(BaseModel):
    id: str
    project_id: str
    title: str
    description: Optional[str]
    status: str
    agent: str
    position: int
    branch_name: Optional[str]
    worktree_path: Optional[str]
    latest_execution: Optional[ExecutionSummary]
    test_results: Optional[dict] = None
    pr_url: Optional[str] = None
    preview_url: Optional[str] = None
    plan_content: Optional[str] = None
    plan_approved_at: Optional[str] = None
    plan_revision: int = 0
    created_at: str
    updated_at: str


# ── Executions ────────────────────────────────────────────────────────────────


class TokenUsage(BaseModel):
    input: int = 0
    output: int = 0
    total: int = 0


class Execution(BaseModel):
    id: str
    task_id: str
    status: str
    agent: str
    pid: Optional[int]
    exit_code: Optional[int]
    started_at: Optional[str]
    finished_at: Optional[str]
    token_usage: Optional[dict]
    error_message: Optional[str]
    created_at: str
    token_input: int = 0
    token_output: int = 0
    cost_usd: float = 0.0
    budget_usd: Optional[float] = None
    budget_exhausted: bool = False
    execution_type: str = "implementation"


# ── Execution Logs ────────────────────────────────────────────────────────────

class LogEntry(BaseModel):
    id: int
    execution_id: str
    sequence: int
    level: str
    content: str
    timestamp: str


# ── Internal (runtime-manager → api) ─────────────────────────────────────────

class InternalEventCreate(BaseModel):
    sequence: int
    level: str
    content: str
    timestamp: str


class InternalStatusUpdate(BaseModel):
    status: str
    pid: Optional[int] = None
    exit_code: Optional[int] = None
    token_usage: Optional[dict] = None
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    budget_usd: Optional[float] = None


class InternalTokenUpdate(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    budget_exhausted: bool = False


class InternalValidationResult(BaseModel):
    passed: int = 0
    failed: int = 0
    errors: int = 0
    details: list[str] = []


# ── Policies ──────────────────────────────────────────────────────────────────

class PolicyCreate(BaseModel):
    pattern: str
    action: str = "warn"    # "warn" | "deny"
    message: str
    enabled: bool = True


class PolicyUpdate(BaseModel):
    pattern: Optional[str] = None
    action: Optional[str] = None
    message: Optional[str] = None
    enabled: Optional[bool] = None


class Policy(BaseModel):
    id: str
    pattern: str
    action: str
    message: str
    enabled: bool
    created_at: str
    updated_at: str


# ── Settings ──────────────────────────────────────────────────────────────────

AVAILABLE_MODELS = [
    {"id": "sonnet", "label": "Claude Sonnet 4.6", "provider": "claude-code"},
    {"id": "opus", "label": "Claude Opus 4.6", "provider": "claude-code"},
    {"id": "haiku", "label": "Claude Haiku 4.5", "provider": "claude-code"},
    {"id": "codex", "label": "OpenAI Codex CLI", "provider": "codex"},
    {"id": "gemini", "label": "Google Gemini CLI", "provider": "gemini"},
]

AVAILABLE_AGENTS = [
    {"id": "claude-code", "label": "Claude Code", "status": "available"},
    {"id": "codex", "label": "OpenAI Codex", "status": "available"},
    {"id": "gemini", "label": "Gemini CLI", "status": "available"},
]


class SettingsRead(BaseModel):
    default_model: str
    default_agent: str
    default_budget_usd: str
    openai_api_key_set: bool   # True if non-empty, never return the actual key
    gemini_api_key_set: bool
    require_approval: bool = False
    github_token_set: bool = False
    github_repo: str = ""
    vercel_token_set: bool = False
    vercel_project_id: str = ""
    auto_deploy: bool = False
    docker_sandbox: bool = False
    # Phase 3: per-stage model overrides
    stage_model_plan: str = "opus"
    stage_model_in_progress: str = "sonnet"
    stage_model_testing: str = "haiku"


class SettingsUpdate(BaseModel):
    default_model: Optional[str] = None
    default_agent: Optional[str] = None
    default_budget_usd: Optional[str] = None
    openai_api_key: Optional[str] = None   # set to "" to clear
    gemini_api_key: Optional[str] = None
    require_approval: Optional[bool] = None
    github_token: Optional[str] = None
    github_repo: Optional[str] = None
    vercel_token: Optional[str] = None
    vercel_project_id: Optional[str] = None
    auto_deploy: Optional[bool] = None
    docker_sandbox: Optional[bool] = None
    # Phase 3: per-stage model overrides
    stage_model_plan: Optional[str] = None
    stage_model_in_progress: Optional[str] = None
    stage_model_testing: Optional[str] = None


# ── Execution (add model/budget override) ────────────────────────────────────

class ExecutionCreate(BaseModel):
    prompt_override: Optional[str] = None
    model_override: Optional[str] = None        # e.g. "opus", "sonnet"
    budget_override: Optional[float] = None     # override per-execution budget cap
