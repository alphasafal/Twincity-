#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL="${WATCHDOG_INTERVAL_SEC:-60}"
echo "live demo watchdog starting (interval=${INTERVAL}s) at $(date -u +%Y-%m-%dT%H:%M:%SZ)"
while true; do
  timeout 200 bash "$ROOT/scripts/keep_live_demo_alive.sh" || true
  sleep "$INTERVAL"
done
