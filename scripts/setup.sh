#!/usr/bin/env bash
# One-time project setup (macOS / Linux)
# Run from repo root: ./scripts/setup.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "========================================"
echo "  Cloud Redundancy AI - One-Time Setup"
echo "========================================"
echo "Project root: $ROOT"
echo ""

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: '$1' not found. $2"
    exit 1
  fi
}

require_cmd python3 "Install Python 3.10+ from https://www.python.org/downloads/"
require_cmd node "Install Node.js 18+ from https://nodejs.org/"
require_cmd npm "Install npm (bundled with Node.js)"

PY_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
PY_MAJOR="${PY_VERSION%%.*}"
PY_MINOR="${PY_VERSION#*.}"
if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  echo "ERROR: Python 3.10+ required (found $PY_VERSION)."
  exit 1
fi
echo "[OK] Python $PY_VERSION"
echo "[OK] Node.js $(node -p process.versions.node)"

echo ""
echo "--- Backend (Python) ---"
if [ ! -d "backend/.venv" ]; then
  echo "Creating virtual environment..."
  python3 -m venv backend/.venv
else
  echo "Virtual environment already exists."
fi

VENV_PY="backend/.venv/bin/python"
"$VENV_PY" -m pip install --upgrade pip
"$VENV_PY" -m pip install -r requirements.txt

echo "Verifying backend imports..."
(cd backend && "$VENV_PY" -c "from app.main import app; print('Backend imports OK')")

echo ""
echo "--- Frontend (Node.js) ---"
(cd frontend && npm install)

echo ""
echo "========================================"
echo "  Setup complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. ./scripts/start-backend.sh"
echo "  2. ./scripts/start-frontend.sh"
echo "  3. Open http://localhost:5173"
echo "  4. Login: admin / ADMIN123"
echo ""
echo "Full guide: SETUP_GUIDE.md"
