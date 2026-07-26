#!/usr/bin/env bash
# Watchdog: keep https://twinpilot.webyaar.in serving for judges.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOSTNAME="${LIVE_DEMO_HOSTNAME:-twinpilot.webyaar.in}"
LOG="${KEEPALIVE_LOG:-/tmp/tp-keepalive.log}"
stamp() { date -u +'%Y-%m-%dT%H:%M:%SZ'; }

need_restart=0

if ! curl -sf --max-time 5 "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
  echo "$(stamp) api down" >>"$LOG"; need_restart=1
fi
if ! curl -sf --max-time 5 "http://127.0.0.1:3000/login" >/dev/null 2>&1; then
  echo "$(stamp) web down" >>"$LOG"; need_restart=1
fi
if ! curl -sf --max-time 5 "http://127.0.0.1:8080/login" >/dev/null 2>&1; then
  echo "$(stamp) proxy down" >>"$LOG"; need_restart=1
fi
if ! pgrep -f 'cloudflared tunnel --config' >/dev/null 2>&1; then
  echo "$(stamp) tunnel process missing" >>"$LOG"; need_restart=1
fi

code=$(curl -s -o /dev/null -m 15 -w '%{http_code}' "https://${HOSTNAME}/login" || true)
if [[ "$code" != "200" && "$code" != "307" && "$code" != "308" && "$code" != "302" ]]; then
  echo "$(stamp) public HTTPS login → HTTP $code" >>"$LOG"; need_restart=1
fi

login_code=$(curl -s -o /dev/null -m 15 -w '%{http_code}' \
  -X POST "https://${HOSTNAME}/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"manager@twinpilot.demo","password":"TwinPilot-Manager-Demo!"}' || true)
if [[ "$login_code" != "200" ]]; then
  echo "$(stamp) public login API → HTTP $login_code" >>"$LOG"; need_restart=1
fi

if [[ "$need_restart" -eq 1 ]]; then
  echo "$(stamp) repairing live demo stack via start_live_demo.sh" >>"$LOG"
  bash "$ROOT/scripts/start_live_demo.sh" >>"$LOG" 2>&1 || true
else
  echo "$(stamp) ok public=$code login_api=$login_code" >>"$LOG"
fi
