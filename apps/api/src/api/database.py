import aiosqlite
import os
from contextlib import asynccontextmanager
from .config import settings

_db_path: str = settings.db_path

DDL = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    repo_path TEXT NOT NULL UNIQUE,
    default_branch TEXT NOT NULL DEFAULT 'main',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'backlog',
    agent TEXT NOT NULL DEFAULT 'claude-code',
    position INTEGER NOT NULL DEFAULT 0,
    branch_name TEXT,
    worktree_path TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON tasks(project_id, status);

CREATE TABLE IF NOT EXISTS executions (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'pending',
    agent TEXT NOT NULL DEFAULT 'claude-code',
    pid INTEGER,
    exit_code INTEGER,
    started_at TEXT,
    finished_at TEXT,
    token_usage TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_executions_task_id ON executions(task_id);

CREATE TABLE IF NOT EXISTS approval_requests (
    id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
    prompt_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL,
    decided_at TEXT
);

CREATE TABLE IF NOT EXISTS execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id TEXT NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
    sequence INTEGER NOT NULL,
    level TEXT NOT NULL DEFAULT 'stdout',
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_logs_execution_seq ON execution_logs(execution_id, sequence);

-- Key-value store for global settings (model defaults, API keys, etc.)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Sprint 5: Context persistence records (prose summaries of past executions)
CREATE TABLE IF NOT EXISTS context_records (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    execution_id TEXT NOT NULL REFERENCES executions(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    outcome TEXT NOT NULL,
    test_results TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_context_records_created ON context_records(created_at DESC);

-- Sprint 6: User-defined policy rules
CREATE TABLE IF NOT EXISTS policies (
    id TEXT PRIMARY KEY,
    pattern TEXT NOT NULL,
    action TEXT NOT NULL DEFAULT 'warn',   -- warn | deny
    message TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


SEED_SETTINGS = [
    ("default_model", "sonnet"),
    ("default_agent", "claude-code"),
    ("default_budget_usd", "2.00"),
    ("openai_api_key", ""),
    ("gemini_api_key", ""),
    ("require_approval", "false"),   # "true" = human-in-the-loop mode
    ("github_token", ""),
    ("github_repo", ""),
    ("vercel_token", ""),
    ("vercel_project_id", ""),
    ("auto_deploy", "false"),
    ("docker_sandbox", "false"),  # Sprint 4: run agents in Docker containers
    # Phase 3: per-stage model defaults
    ("stage_model_plan", "opus"),
    ("stage_model_in_progress", "sonnet"),
    ("stage_model_testing", "haiku"),
]


async def _migrate(db: aiosqlite.Connection) -> None:
    """Add columns introduced in Phase 2 to existing databases."""
    migrations = [
        "ALTER TABLE executions ADD COLUMN token_input INTEGER DEFAULT 0",
        "ALTER TABLE executions ADD COLUMN token_output INTEGER DEFAULT 0",
        "ALTER TABLE executions ADD COLUMN cost_usd REAL DEFAULT 0.0",
        "ALTER TABLE executions ADD COLUMN budget_usd REAL",
        "ALTER TABLE executions ADD COLUMN budget_exhausted INTEGER DEFAULT 0",
        "ALTER TABLE executions ADD COLUMN execution_type TEXT NOT NULL DEFAULT 'implementation'",
        "ALTER TABLE tasks ADD COLUMN pr_url TEXT",
        "ALTER TABLE tasks ADD COLUMN preview_url TEXT",
        "ALTER TABLE tasks ADD COLUMN github_repo TEXT",
        "ALTER TABLE tasks ADD COLUMN test_results TEXT",  # JSON: {passed, failed, errors, details}
        # Sprint 6: Regression memory extensions
        "ALTER TABLE context_records ADD COLUMN regression_type TEXT",  # test_failure|build_failure|timeout|budget_exhausted
        "ALTER TABLE context_records ADD COLUMN error_pattern TEXT",    # failing test name / error keyword
        # Phase 3: Pipeline stages — plan artifact columns
        "ALTER TABLE tasks ADD COLUMN plan_content TEXT",
        "ALTER TABLE tasks ADD COLUMN plan_approved_at TEXT",
        "ALTER TABLE tasks ADD COLUMN plan_revision INTEGER DEFAULT 0",
        # Phase 3: migrate legacy 'review' status -> 'testing'
        "UPDATE tasks SET status = 'testing' WHERE status = 'review'",
    ]
    for sql in migrations:
        try:
            await db.execute(sql)
        except Exception:
            pass  # column already exists


def _load_sqlite_vec(db_conn) -> bool:
    """Load sqlite-vec extension on the raw sqlite3 connection. Returns True on success."""
    try:
        import sqlite_vec  # type: ignore
        db_conn.enable_load_extension(True)
        sqlite_vec.load(db_conn)
        db_conn.enable_load_extension(False)
        return True
    except Exception:
        return False


async def init_db() -> None:
    os.makedirs(os.path.dirname(os.path.abspath(_db_path)), exist_ok=True)
    async with aiosqlite.connect(_db_path) as db:
        # Load sqlite-vec extension (Sprint 5 vector search)
        vec_ok = _load_sqlite_vec(db._db)  # access underlying sqlite3.Connection
        await db.executescript(DDL)
        await _migrate(db)

        # Create vec0 virtual table if sqlite-vec is available
        if vec_ok:
            try:
                await db.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS context_embeddings "
                    "USING vec0(embedding FLOAT[1536])"
                )
                await db.commit()
            except Exception as e:
                print(f"[db] Failed to create context_embeddings vec table: {e}")

        # Seed default settings rows (INSERT OR IGNORE — never overwrites user values)
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        await db.executemany(
            "INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
            [(k, v, now) for k, v in SEED_SETTINGS],
        )
        await db.commit()


@asynccontextmanager
async def get_db():
    async with aiosqlite.connect(_db_path) as db:
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA foreign_keys = ON")
        _load_sqlite_vec(db._db)  # load extension on every connection (no-op if unavailable)
        yield db
