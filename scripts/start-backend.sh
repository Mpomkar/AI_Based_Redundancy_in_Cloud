#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VENV_PY="$ROOT/backend/.venv/bin/python"

if [ ! -f "$VENV_PY" ]; then
  echo "Virtual environment not found. Run ./scripts/setup.sh first."
  exit 1
fi

LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
echo "Starting backend (shared SQLite + uploads on THIS machine)"
echo "  Local: http://127.0.0.1:8000"
echo "  Docs:  http://127.0.0.1:8000/docs"
if [ -n "${LAN_IP:-}" ]; then
  echo "  LAN:   http://${LAN_IP}:8000"
fi
echo "Other systems must use THIS backend to see the same admin files."

cd "$ROOT/backend"
exec "$VENV_PY" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
