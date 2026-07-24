#!/usr/bin/env bash
# Start TwinPilot demo: API (uvicorn) + Next.js web
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

if [[ ! -d "$ROOT/.venv" ]]; then
  echo "Virtualenv missing — run: make setup"
  exit 1
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"

if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
fi
if [[ ! -f "$ROOT/apps/web/.env.local" ]]; then
  cp "$ROOT/apps/web/.env.local.example" "$ROOT/apps/web/.env.local"
fi

cleanup() {
  echo ""
  echo "Stopping TwinPilot demo..."
  [[ -n "${API_PID:-}" ]] && kill "$API_PID" 2>/dev/null || true
  [[ -n "${WEB_PID:-}" ]] && kill "$WEB_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "==> Starting TwinPilot API on :8000"
cd "$ROOT/services/api"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
API_PID=$!

# Wait for health
for i in $(seq 1 40); do
  if curl -sf http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "API healthy"
    break
  fi
  sleep 0.5
  if [[ "$i" -eq 40 ]]; then
    echo "API failed to become healthy"
    exit 1
  fi
done

echo "==> Starting TwinPilot Web on :3000"
cd "$ROOT"
pnpm --filter @twinpilot/web dev &
WEB_PID=$!

echo ""
echo "TwinPilot demo is running (simulated data)."
echo "  Web:  http://localhost:3000"
echo "  API:  http://localhost:8000"
echo "  Docs: http://localhost:8000/docs"
echo ""
echo "Login (dev only):"
echo "  manager@twinpilot.demo / TwinPilot-Manager-Demo!"
echo ""
echo "Press Ctrl+C to stop."

wait
