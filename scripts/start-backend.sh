#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PY="$ROOT/backend/.venv/bin/python"

if [ ! -f "$VENV_PY" ]; then
  echo "Virtual environment not found. Run ./scripts/setup.sh first."
  exit 1
fi

echo "Starting backend at http://127.0.0.1:8000"
cd "$ROOT/backend"
exec "$VENV_PY" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
