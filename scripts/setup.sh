#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "Setting up arun-kanban in $ROOT"

# ── Create .env if missing ───────────────────────────────────────────────────
if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "Created .env from .env.example — review and adjust paths if needed"
fi

# ── Node deps ─────────────────────────────────────────────────────────────────
echo ""
echo "Installing Node.js dependencies..."
cd "$ROOT"
npm install

# ── Python: agent-adapters ───────────────────────────────────────────────────
echo ""
echo "Setting up agent-adapters Python package..."
cd "$ROOT/packages/agent-adapters"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -e . --quiet

# ── Python: api ──────────────────────────────────────────────────────────────
echo ""
echo "Setting up API Python environment..."
cd "$ROOT/apps/api"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -e . --quiet

# ── Python: runtime-manager ──────────────────────────────────────────────────
echo ""
echo "Setting up runtime-manager Python environment..."
cd "$ROOT/apps/runtime-manager"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# Install agent-adapters into runtime-manager venv
.venv/bin/pip install -e "$ROOT/packages/agent-adapters" --quiet
.venv/bin/pip install -e . --quiet

# ── Data dir ─────────────────────────────────────────────────────────────────
echo ""
echo "Creating data and workspaces directories..."
mkdir -p "$ROOT/data" "$ROOT/workspaces"

echo ""
echo "✓ Setup complete."
echo ""
echo "Next steps:"
echo "  1. Edit $ROOT/.env — set WORKSPACES_ROOT and verify CLAUDE_BIN"
echo "  2. Run: ./scripts/dev.sh"
echo "  3. Open: http://localhost:3000"
