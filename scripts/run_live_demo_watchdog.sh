#!/usr/bin/env bash
# Long-running watchdog loop (no cron required).
# Keeps https://twinpilot.webyaar.in healthy while this process is alive.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL="${WATCHDOG_INTERVAL_SEC:-60}"
echo "live demo watchdog starting (interval=${INTERVAL}s)"
while true; do
  bash "$ROOT/scripts/keep_live_demo_alive.sh" || true
  sleep "$INTERVAL"
done
