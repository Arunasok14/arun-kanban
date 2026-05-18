# AI Agent Control Plane — Handover Document
**Date:** 2026-05-17
**Status:** Phase 2, Sprints 1 & 2 complete. Sprints 3–7 remaining.

---

## What This Project Is

An **AI Agent Control Plane** — a Kanban board that orchestrates external CLI coding agents (Claude Code, OpenAI Codex, Google Gemini) to autonomously execute software engineering tasks in isolated git worktrees. The system does NOT generate code itself — it delegates to CLI tools.

**Core loop:**
1. Operator creates a project (points to a git repo) and tasks on a Kanban board
2. Operator clicks "Run Agent" on a task
3. System creates a git worktree, writes a TASK_CONTEXT.md prompt file, starts the CLI agent
4. Agent output streams live to the UI via WebSocket
5. Agent auto-commits changes; system tracks token cost

---

## Monorepo Layout

```
/Users/arun/Documents/claude/arun-kanban/
├── apps/
│   ├── api/                          # FastAPI, port 8000
│   │   └── src/api/
│   │       ├── main.py               # App, CORS, lifespan, router registration
│   │       ├── database.py           # aiosqlite DDL + Phase 2 migrations
│   │       ├── schemas.py            # Pydantic models (all)
│   │       ├── bus.py                # asyncio.Queue pub/sub EventBus
│   │       ├── queue.py              # Redis sorted-set task queue
│   │       ├── config.py             # Settings (db_path, redis_url, runtime_manager_url)
│   │       ├── routers/
│   │       │   ├── projects.py       # CRUD
│   │       │   ├── tasks.py          # CRUD + status validation
│   │       │   ├── executions.py     # Start/stop + internal event/status/tokens/approval endpoints
│   │       │   ├── approvals.py      # GET list, POST decide + internal approval_request
│   │       │   ├── websocket.py      # WS log replay + live fan-out
│   │       │   └── settings.py       # GET/PATCH settings, /models, /agents
│   │       └── services/
│   │           ├── execution_service.py   # create, get, apply_status, apply_event, update_token_usage
│   │           ├── task_service.py
│   │           ├── project_service.py
│   │           └── settings_service.py    # get, get_value, update
│   │
│   ├── runtime-manager/              # FastAPI, port 8001
│   │   └── src/runtime_manager/
│   │       ├── main.py               # RunRequest, /run, /stop, /signal/approval, queue worker lifespan
│   │       ├── runner.py             # run_execution() — worktree + adapter + token reporting
│   │       ├── approval_registry.py  # asyncio.Future registry for human approvals
│   │       ├── worktree_manager.py   # git worktree CRUD + commit_changes
│   │       ├── context_injector.py   # Writes TASK_CONTEXT.md prompt
│   │       ├── process_manager.py    # PID registry (adapter references)
│   │       └── config.py             # api_url, claude_bin, redis_url, queue_poll_interval
│   │
│   └── web/                          # Next.js 15, port 3000
│       ├── app/
│       │   ├── projects/page.tsx              # Project list
│       │   ├── projects/[projectId]/page.tsx  # Kanban board
│       │   └── settings/page.tsx             # Settings page
│       ├── components/
│       │   ├── board/   KanbanBoard, KanbanColumn, TaskCard
│       │   ├── task/
│       │   │   ├── TaskDetailPanel.tsx        # Right drawer
│       │   │   ├── ExecutionControls.tsx      # Run/Stop + model selector
│       │   │   ├── ExecutionLogViewer.tsx     # Live ANSI log stream
│       │   │   ├── TokenBudgetPanel.tsx       # ✅ Sprint 1 — cost/budget bar
│       │   │   └── ApprovalPanel.tsx          # ✅ Sprint 2 — y/n popup with countdown
│       │   ├── project/  CreateProjectModal
│       │   └── ui/       Badge, etc.
│       ├── hooks/
│       │   └── useExecutionStream.ts   # WS hook → logs, execStatus, tokens, pendingApproval
│       ├── lib/
│       │   ├── api-client.ts          # All REST calls incl. approvals
│       │   └── constants.ts
│       ├── store/boardStore.ts        # Zustand board state
│       └── types/index.ts             # All TypeScript types
│
└── packages/
    └── agent-adapters/src/agent_adapters/
        ├── base.py                    # Abstract AgentAdapter
        ├── types.py                   # AgentEvent, AgentStatus, EventLevel
        ├── claude_adapter.py          # Full stream-json impl + approval intercept
        ├── codex_adapter.py           # Full subprocess impl + stderr drain
        └── gemini_adapter.py          # Full subprocess impl + stderr drain
```

---

## Database Schema (SQLite — `/data/kanban.db`)

```sql
projects (id, name, description, repo_path, default_branch, created_at, updated_at)

tasks (id, project_id, title, description, status, agent, position,
       branch_name, worktree_path,
       pr_url, preview_url, github_repo,        -- Sprint 7 columns
       created_at, updated_at)

executions (id, task_id, status, agent, pid, exit_code,
            started_at, finished_at, token_usage, error_message, created_at,
            -- Phase 2 additions:
            token_input, token_output, cost_usd, budget_usd, budget_exhausted,
            execution_type)                      -- 'implementation' | 'validation'

execution_logs (id, execution_id, sequence, level, content, timestamp)
  -- level: stdout | stderr | system | tool_use

approval_requests (id, execution_id, prompt_text, status, created_at, decided_at)
  -- status: pending | approved | denied | timeout

settings (key, value, updated_at)
  -- keys: default_model, default_agent, default_budget_usd,
  --        openai_api_key, gemini_api_key, require_approval,
  --        github_token, github_repo, vercel_token, vercel_project_id, auto_deploy
```

---

## API Endpoints (all working)

```
# Projects
GET/POST  /api/v1/projects
GET/PATCH/DELETE /api/v1/projects/{id}

# Tasks
GET/POST  /api/v1/projects/{id}/tasks
GET/PATCH/DELETE /api/v1/tasks/{id}

# Executions
POST   /api/v1/tasks/{id}/executions         → enqueues to Redis
GET    /api/v1/executions/{id}
GET    /api/v1/tasks/{id}/executions
POST   /api/v1/executions/{id}/stop

# Approvals (Sprint 2)
GET    /api/v1/executions/{id}/approvals
POST   /api/v1/approvals/{approval_id}/decide   { approved: bool }

# Logs (polling fallback)
GET    /api/v1/executions/{id}/logs?after_sequence=N

# WebSocket
WS     /ws/executions/{id}

# Settings
GET/PATCH /api/v1/settings
GET       /api/v1/settings/models
GET       /api/v1/settings/agents

# Internal (runtime-manager → api only)
POST   /api/internal/executions/{id}/events
POST   /api/internal/executions/{id}/status
POST   /api/internal/executions/{id}/tokens
POST   /api/internal/executions/{id}/approval_request
```

---

## WebSocket Wire Protocol

```json
{ "type": "log", "sequence": 1, "level": "stdout|stderr|system|tool_use", "content": "...", "timestamp": "..." }
{ "type": "status", "status": "running", "pid": 12345, "token_input": 100, "token_output": 50, "cost_usd": 0.002 }
{ "type": "tokens", "token_input": 500, "token_output": 200, "cost_usd": 0.0045, "budget_usd": 2.0, "budget_exhausted": false }
{ "type": "approval_request", "approval_id": "uuid", "prompt_text": "Do you want to run bash command: ...? [y/n]" }
{ "type": "approval_decided", "approval_id": "uuid", "approved": true }
{ "type": "approval_timeout", "approval_id": "uuid" }
{ "type": "done", "status": "completed|failed|stopped", "exit_code": 0, "token_usage": {...} }
{ "type": "ping" }
```

---

## Services Running

| Service | Port | Start Command |
|---------|------|---------------|
| Redis | 6379 | `brew services start redis` |
| API | 8000 | `cd apps/api && PYTHONPATH=src .venv/bin/uvicorn api.main:app --reload` |
| Runtime Manager | 8001 | `cd apps/runtime-manager && PYTHONPATH=src:../../packages/agent-adapters/src .venv/bin/uvicorn runtime_manager.main:app --reload` |
| Web | 3000 | `cd apps/web && npm run dev` |
| All-in-one | — | `./scripts/dev.sh` |

---

## Environment

- macOS Darwin 25.4.0, zsh
- Node.js v25.9, Python 3.14
- Claude CLI v2.1.84 at `/opt/homebrew/bin/claude`
- Docker: NOT installed (Sprint 4 installs it via `brew install --cask docker`)
- Redis: installed and running (`brew services start redis`)
- Each Python service has its own `.venv/` inside its directory
- TypeScript: zero errors across web app

---

## What's DONE (Phases 1 + 2 Sprints 1–2)

### Phase 1 (complete)
- Full Kanban board: drag-and-drop, 4 columns (backlog/in_progress/review/done)
- Project + Task CRUD
- Claude Code CLI integration (stream-json output, ANSI log rendering)
- Git worktree isolation per task
- WebSocket live streaming + log replay
- Auto-commit after execution
- Settings: model selection, budget cap, API keys for Codex/Gemini

### Sprint 1 — Token Orchestration Engine ✅
- Redis sorted-set queue: API enqueues → runtime-manager polls & dispatches
- New DB columns: `token_input`, `token_output`, `cost_usd`, `budget_usd`, `budget_exhausted`
- Per-usage-event token accumulation with model cost rates
- Budget enforcement: stops adapter when `total_cost >= max_budget_usd`
- `POST /api/internal/executions/{id}/tokens` endpoint
- `"tokens"` WS frame type
- `TokenBudgetPanel.tsx` — progress bar, cost display, "Budget exhausted" badge
- Codex adapter: full subprocess + concurrent stderr drain + `--quiet` flag
- Gemini adapter: full subprocess + concurrent stderr drain + `--yolo` flag
- Codex/Gemini marked as `available` in settings

### Sprint 2 — Human Approval Workflow ✅
- `approval_registry.py`: asyncio.Future per approval_id, 5-min timeout → auto-deny
- Claude adapter: `skip_permissions` flag; detects `[y/n]` prompts via regex; writes `y\n`/`n\n` to stdin
- `/signal/approval/{id}` endpoint on runtime-manager
- `approvals.py` router: list, decide, internal registration
- `approval_requests` DB table
- `require_approval` setting propagated to `skip_permissions` in execution payload
- `ApprovalPanel.tsx`: amber popup, countdown timer, Approve/Deny buttons
- `pendingApproval` state in `useExecutionStream` hook
- Settings UI: "Safety & Approval" section with toggle

---

## What's REMAINING (Sprints 3–7)

### Sprint 3 — Independent Testing Agent + Full Gemini Adapter
**Goal:** Auto-spawn validation execution after implementation completes; parse test results.

Key tasks:
1. In `internal_status` handler (`executions.py`): when `status=="completed"` and `execution_type=="implementation"` → `asyncio.create_task(_spawn_validation(...))`
2. `_spawn_validation()`: creates new execution with `execution_type="validation"`, `agent="claude-code"`, prompt = "Run all tests. Do not modify source files."
3. Add `skip_worktree_commit: bool` and `skip_context_inject: bool` to `RunRequest` + `run_execution()`
4. Validation runs in **same worktree** as implementation (no new worktree)
5. `TestResultsPanel.tsx` — parse logs for `✓ N passing` / `✗ N failing`, show badge on TaskCard
6. New WS frame: `{ "type": "validation_started", "execution_id": "..." }`
7. `TaskCard` shows green/red test badge after validation

Files to modify:
- `apps/api/src/api/routers/executions.py` — add `_spawn_validation()` + trigger
- `apps/runtime-manager/src/runtime_manager/main.py` — add fields to RunRequest
- `apps/runtime-manager/src/runtime_manager/runner.py` — honor skip flags
- `apps/web/components/task/TestResultsPanel.tsx` — NEW
- `apps/web/components/board/TaskCard.tsx` — add test badge
- `apps/web/types/index.ts` — add `validation_started` WsFrame type

### Sprint 4 — Docker Sandbox Runtime
**Goal:** Run agents inside Docker containers with resource limits.

Key tasks:
1. `brew install --cask docker` (user must do this, Docker Desktop must be running)
2. `pip install docker` in runtime-manager venv
3. `docker_runner.py` — NEW: `run_in_container()` async generator
4. `Dockerfile.agent` in repo root — image with claude-code, codex, gemini CLIs
5. `RunRequest` + `run_execution()`: add `use_docker: bool = False`
6. Runner: if `use_docker`, delegate stdout/stderr bytes from docker container instead of subprocess
7. Settings: `use_docker` setting key + toggle in UI

Files:
- `apps/runtime-manager/src/runtime_manager/docker_runner.py` — NEW
- `apps/runtime-manager/src/runtime_manager/runner.py` — docker branch
- `apps/api/src/api/database.py` — seed `use_docker: false`
- `apps/web/app/settings/page.tsx` — Docker toggle section

### Sprint 5 — Context Persistence Engine (sqlite-vec)
**Goal:** Vector embeddings of past task outcomes; inject as "Prior Work" into new prompts.

Key tasks:
1. `pip install sqlite-vec` in api venv
2. New DB tables: `context_embeddings` (vec0 virtual table), `context_records`
3. `embedding_service.py` — NEW: `embed()` (OpenAI text-embedding-3-small if key set, else sentence-transformers fallback), `record_execution()`, `retrieve_similar()`
4. Call `record_execution()` in `internal_status` when completed/failed
5. Call `retrieve_similar()` in `start_execution()` before enqueuing → pass `prior_context` in payload
6. `context_injector.py` — add `## Prior Work` section if prior_context provided
7. Add `execution_id` to RunRequest for context lookup

Files:
- `apps/api/src/api/services/embedding_service.py` — NEW
- `apps/api/src/api/database.py` — new DDL for context tables
- `apps/api/src/api/routers/executions.py` — trigger record + retrieve
- `apps/runtime-manager/src/runtime_manager/context_injector.py` — prior_context section
- `apps/runtime-manager/src/runtime_manager/main.py` — RunRequest.prior_context

### Sprint 6 — Regression Memory + Policy Engine
**Goal:** Remember failures; block dangerous operations before they reach Claude.

Key tasks:
1. Extend `context_records` with `regression_type`, `error_pattern` columns
2. After validation fails: parse failing test names → insert regression records
3. Context injector: query regressions for task's files → prepend `⚠️ Regression Warning`
4. `policy_engine.py` — NEW: regex-based DENY/WARN rules
5. Policy evaluated in `approval_registry.request_approval()` before creating Future
6. DENY → immediately write `n\n` to stdin + emit system log
7. WARN → escalate to human approval
8. Settings UI: "Policies" section listing rules with toggle + custom pattern input

Files:
- `apps/api/src/api/services/policy_engine.py` — NEW
- `apps/runtime-manager/src/runtime_manager/approval_registry.py` — call policy check
- `apps/api/src/api/database.py` — migration for regression columns
- `apps/web/app/settings/page.tsx` — Policies section

### Sprint 7 — Deployment Engine (GitHub PR + Vercel Preview)
**Goal:** After passing tests, auto-create PR and optionally deploy to Vercel.

Key tasks:
1. `github_service.py` — NEW: `create_pr()`, `push_branch()`
2. `vercel_service.py` — NEW: `trigger_deploy()`, `poll_deployment()`
3. In `internal_status`: when validation `status=="completed"` + tests passing:
   - `worktree_manager.push_branch()` → `github_service.create_pr()` → store `tasks.pr_url`
   - If `auto_deploy`: `vercel_service.trigger_deploy()` → poll → store `tasks.preview_url`
   - Publish WS frame: `{ "type": "deployment", "pr_url": "...", "preview_url": "..." }`
4. `TaskCard.tsx` — PR link badge + Preview badge
5. Settings: Deployment section (GitHub token, repo, Vercel token, project ID, auto_deploy toggle)

Files:
- `apps/api/src/api/services/github_service.py` — NEW
- `apps/api/src/api/services/vercel_service.py` — NEW
- `apps/api/src/api/routers/executions.py` — deployment trigger in `internal_status`
- `apps/runtime-manager/src/runtime_manager/worktree_manager.py` — add `push_branch()`
- `apps/web/components/board/TaskCard.tsx` — PR + preview badges
- `apps/web/types/index.ts` — `deployment` WsFrame type

---

## Key Architectural Patterns

### Execution Flow
```
UI click Run → POST /api/v1/tasks/{id}/executions
  → execution_service.create() → DB row (status=pending)
  → task_queue.enqueue(payload) → Redis sorted set
  → return execution to UI immediately

runtime-manager queue worker (polls every 0.5s):
  → dequeue() → asyncio.create_task(run_execution(...))
  → _post_status(running) → worktree_manager.create_worktree()
  → context_injector.inject() → TASK_CONTEXT.md
  → _build_adapter() → adapter.run() [async generator]
  → each event → _post_event() → DB + bus.publish() → WS fans out
  → usage event → _post_tokens() → budget check → stop if exhausted
  → process_exit → auto-commit → _post_status(completed/failed)
  → if implementation + completed → _spawn_validation() [Sprint 3]
  → if tests pass → create_pr() + trigger_deploy() [Sprint 7]
```

### Approval Flow (Sprint 2)
```
Claude stdout: "Do you want to...? [y/n]"
  → claude_adapter detects regex
  → approval_registry.request_approval(api_url, execution_id, approval_id, text)
    → POST /api/internal/.../approval_request → DB + WS approval_request frame
    → await asyncio.Future (max 5 min)

UI sees approval_request WS frame → ApprovalPanel appears
Operator clicks Approve/Deny → POST /api/v1/approvals/{id}/decide
  → DB updated → POST /runtime-manager/signal/approval/{id}
  → approval_registry.resolve() → Future.set_result(approved)
  → claude_adapter writes y\n or n\n to stdin
  → WS approval_decided frame → ApprovalPanel dismisses
```

### Token Budget Flow
```
Claude emits: {"type": "usage", "input_tokens": 500, "output_tokens": 200}
  → runner accumulates total_input/total_output
  → _compute_cost(model, inp, out) using MODEL_COSTS dict
  → POST /api/internal/.../tokens {input, output, cost_usd, budget_exhausted}
  → DB: token_input += inp, token_output += out, cost_usd += cost
  → WS "tokens" frame → TokenBudgetPanel updates live
  → if budget_exhausted: adapter.stop() → status = "stopped"
```

---

## Model Cost Rates (per million tokens)

| Model | Input | Output |
|-------|-------|--------|
| sonnet | $3.00 | $15.00 |
| opus | $15.00 | $75.00 |
| haiku | $0.25 | $1.25 |

---

## Python Package Structure

Each service has its own `.venv/`. Import paths:
- API: `PYTHONPATH=apps/api/src` → `from api.xxx import ...`
- Runtime-manager: `PYTHONPATH=apps/runtime-manager/src:packages/agent-adapters/src` → `from runtime_manager.xxx` and `from agent_adapters.xxx`
- The `packages/agent-adapters` package is NOT installed via .pth in Python 3.14 venvs — must be in PYTHONPATH explicitly

---

## Important Notes for Next Session

1. **Redis must be running**: `redis-cli ping` should return `PONG`. If not: `brew services start redis`
2. **Port conflicts**: kill stale processes before starting: `pkill -f "uvicorn api.main"` and `pkill -f "uvicorn runtime_manager"`
3. **DB migrations run automatically** on API startup via `_migrate()` in `database.py` — safe to re-run
4. **No Alembic** — all schema changes go in `_migrate()` wrapped in try/except (column already exists is safe to ignore)
5. **TypeScript**: always run `npx tsc --noEmit` after frontend changes — currently zero errors
6. **`execution_type` column**: defaults to `'implementation'`. Sprint 3 sets it to `'validation'` for test runner executions
7. **`skip_permissions`**: defaults to `True` (safe/fast mode). Setting `require_approval=true` in settings flips it to `False`
8. **Queue worker** in runtime-manager polls Redis every 0.5s in a background asyncio task started in `lifespan()`
9. **The `/run` HTTP endpoint** on runtime-manager is kept as a fallback but primary flow goes through Redis queue
