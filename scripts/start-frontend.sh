#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "node_modules not found. Run ./scripts/setup.sh first."
  exit 1
fi

echo "Starting frontend at http://localhost:5173"
cd "$ROOT/frontend"
exec npm run dev
