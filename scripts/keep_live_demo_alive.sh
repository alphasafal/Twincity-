#!/usr/bin/env bash
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOSTNAME="${LIVE_DEMO_HOSTNAME:-twinpilot.webyaar.in}"
LOG="${KEEPALIVE_LOG:-/tmp/tp-keepalive.log}"
stamp() { date -u +'%Y-%m-%dT%H:%M:%SZ'; }
need_restart=0
curl_ok() { curl -sf --max-time 8 "$@" >/dev/null 2>&1; }

if ! curl_ok "http://127.0.0.1:8000/health"; then echo "$(stamp) api down" >>"$LOG"; need_restart=1; fi
if ! curl_ok "http://127.0.0.1:3000/login"; then echo "$(stamp) web down" >>"$LOG"; need_restart=1; fi
if ! curl_ok "http://127.0.0.1:8080/login"; then echo "$(stamp) proxy down" >>"$LOG"; need_restart=1; fi
if ! pgrep -f 'cloudflared tunnel --config' >/dev/null 2>&1; then echo "$(stamp) tunnel missing" >>"$LOG"; need_restart=1; fi

code=$(curl -s -o /dev/null -m 12 -w '%{http_code}' "https://${HOSTNAME}/login" || true)
if [[ "$code" != "200" && "$code" != "307" && "$code" != "308" && "$code" != "302" ]]; then
  echo "$(stamp) public login → HTTP $code" >>"$LOG"; need_restart=1
fi
login_code=$(curl -s -o /dev/null -m 12 -w '%{http_code}' \
  -X POST "https://${HOSTNAME}/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"manager@twinpilot.demo","password":"TwinPilot-Manager-Demo!"}' || true)
if [[ "$login_code" != "200" ]]; then
  echo "$(stamp) public login API → HTTP $login_code" >>"$LOG"; need_restart=1
fi

if [[ "$need_restart" -eq 1 ]]; then
  echo "$(stamp) repairing via start_live_demo.sh" >>"$LOG"
  timeout 180 bash "$ROOT/scripts/start_live_demo.sh" >>"$LOG" 2>&1 || echo "$(stamp) repair failed" >>"$LOG"
else
  echo "$(stamp) ok public=$code login_api=$login_code" >>"$LOG"
fi
tail -n 200 "$LOG" > "${LOG}.tmp" 2>/dev/null && mv "${LOG}.tmp" "$LOG" || true
