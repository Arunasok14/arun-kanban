#!/usr/bin/env bash
# Build the kanban-agent Docker sandbox image.
# Run from anywhere in the monorepo.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Building kanban-agent:latest from $ROOT/Dockerfile.agent ..."
docker build -f "$ROOT/Dockerfile.agent" -t kanban-agent:latest "$ROOT"
echo ""
echo "Done. Verify with: docker images kanban-agent"
echo "Then enable 'Docker Sandbox' in Settings."
