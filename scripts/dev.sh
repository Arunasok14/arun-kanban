#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Load .env
if [ -f "$ROOT/.env" ]; then
  set -a
  source "$ROOT/.env"
  set +a
fi

cleanup() {
  echo ""
  echo "Shutting down services..."
  kill 0
}
trap cleanup SIGINT SIGTERM

echo "Starting arun-kanban services..."
echo ""

# ── Redis ─────────────────────────────────────────────────────────────────────
if ! redis-cli ping &>/dev/null; then
  echo "Starting Redis..."
  brew services start redis
  sleep 1
fi

# ── API (FastAPI on port 8000) ────────────────────────────────────────────────
cd "$ROOT/apps/api"
PYTHONPATH="$ROOT/apps/api/src" \
  "$ROOT/apps/api/.venv/bin/uvicorn" api.main:app \
  --host 0.0.0.0 --port 8000 --reload \
  2>&1 | sed 's/^/[api] /' &

sleep 1

# ── Runtime Manager (FastAPI on port 8001) ────────────────────────────────────
cd "$ROOT/apps/runtime-manager"
# Include agent-adapters/src explicitly (Python 3.14 venv .pth workaround)
PYTHONPATH="$ROOT/apps/runtime-manager/src:$ROOT/packages/agent-adapters/src" \
  "$ROOT/apps/runtime-manager/.venv/bin/uvicorn" runtime_manager.main:app \
  --host 0.0.0.0 --port 8001 --reload \
  2>&1 | sed 's/^/[runtime] /' &

sleep 1

# ── Next.js (port 3000) ───────────────────────────────────────────────────────
cd "$ROOT/apps/web"
npm run dev 2>&1 | sed 's/^/[web] /' &

echo ""
echo "Services started:"
echo "  Redis:           localhost:6379"
echo "  API:             http://localhost:8000"
echo "  Runtime Manager: http://localhost:8001"
echo "  Web:             http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop all services."
echo ""

wait
