#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -d "$ROOT/frontend/node_modules" ]; then
  echo "node_modules not found. Run ./scripts/setup.sh first."
  exit 1
fi

LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
echo "Starting frontend (Vite — reachable on LAN)"
echo "  Local: http://localhost:5173"
if [ -n "${LAN_IP:-}" ]; then
  echo "  LAN:   http://${LAN_IP}:5173"
fi
echo "Data is shared when all browsers talk to the SAME backend on this machine."

cd "$ROOT/frontend"
exec npm run dev -- --host
