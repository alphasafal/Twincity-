#!/usr/bin/env bash
# TwinPilot end-to-end demo replay against a running API (or starts one).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

API_URL="${TWINPILOT_API_URL:-http://127.0.0.1:8000}"
HELPER="$ROOT/infrastructure/scripts/replay_lib.py"
STARTED_API=0
API_PID=""

cleanup() {
  if [[ "$STARTED_API" -eq 1 && -n "${API_PID}" ]]; then
    kill "$API_PID" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

log() { printf '\n==> %s\n' "$*"; }
ok() { printf '    ✓ %s\n' "$*"; }

if [[ ! -d "$ROOT/.venv" ]]; then
  echo "Virtualenv missing — run: make setup"
  exit 1
fi
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"

if ! curl -sf "$API_URL/health" >/dev/null 2>&1; then
  log "API not healthy at $API_URL — starting local uvicorn"
  if [[ ! -f "$ROOT/.env" ]]; then
    cp "$ROOT/.env.example" "$ROOT/.env"
  fi
  rm -f "$ROOT/services/api/twinpilot.db"
  (
    cd "$ROOT/services/api"
    uvicorn app.main:app --host 127.0.0.1 --port 8000
  ) &
  API_PID=$!
  STARTED_API=1
  for i in $(seq 1 60); do
    if curl -sf "$API_URL/health" >/dev/null 2>&1; then
      ok "API ready"
      break
    fi
    sleep 0.5
    if [[ "$i" -eq 60 ]]; then
      echo "API failed to start"
      exit 1
    fi
  done
else
  ok "Using existing API at $API_URL"
fi

log "Login as facility manager"
LOGIN=$(curl -sf -X POST "$API_URL/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"manager@twinpilot.demo","password":"TwinPilot-Manager-Demo!"}')
TOKEN=$(printf '%s' "$LOGIN" | python3 "$HELPER" token)
AUTH="Authorization: Bearer $TOKEN"

ADMIN_LOGIN=$(curl -sf -X POST "$API_URL/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@twinpilot.demo","password":"TwinPilot-Admin-Demo!"}')
ADMIN_TOKEN=$(printf '%s' "$ADMIN_LOGIN" | python3 "$HELPER" token)
ADMIN_AUTH="Authorization: Bearer $ADMIN_TOKEN"
ok "Authenticated"

BID=$(curl -sf "$API_URL/api/v1/buildings" -H "$AUTH" | python3 "$HELPER" building_id)
ok "Building $BID"

log "Reset demo + normal hot day scenario"
curl -sf -X POST "$API_URL/api/v1/demo/scenarios/reset" -H "$AUTH" >/dev/null
curl -sf -X POST "$API_URL/api/v1/demo/scenarios/normal_hot_day/start" -H "$AUTH" >/dev/null
curl -sf "$API_URL/api/v1/buildings/$BID/status" -H "$AUTH" | python3 "$HELPER" status

log "Generate / simulate / validate / approve / apply (ADVISORY path)"
curl -sf -X PATCH "$API_URL/api/v1/buildings/$BID/mode" -H "$ADMIN_AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"mode":"ADVISORY","reason":"Replay script advisory path"}' >/dev/null
PLANS=$(curl -sf -X POST "$API_URL/api/v1/buildings/$BID/optimization/generate" -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"energy_weight":0.25,"cost_weight":0.2,"carbon_weight":0.2,"comfort_weight":0.2,"peak_weight":0.1,"equipment_weight":0.05}')
PID=$(printf '%s' "$PLANS" | python3 "$HELPER" balanced_plan_id)
ok "Balanced plan $PID"
curl -sf -X POST "$API_URL/api/v1/control-plans/$PID/simulate" -H "$AUTH" >/dev/null
ok "Simulated"
curl -sf -X POST "$API_URL/api/v1/control-plans/$PID/validate" -H "$AUTH" >/dev/null
curl -sf -X POST "$API_URL/api/v1/control-plans/$PID/approve" -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"reason":"Replay approval"}' >/dev/null
ok "Approved"
curl -sf -X POST "$API_URL/api/v1/control-plans/$PID/apply" -H "$AUTH" | python3 "$HELPER" apply

log "Sensor-fault scenario → Guarded mode"
curl -sf -X POST "$API_URL/api/v1/demo/scenarios/reset" -H "$AUTH" >/dev/null
curl -sf -X POST "$API_URL/api/v1/demo/scenarios/faulty_sensor/start" -H "$AUTH" >/dev/null
sleep 3
curl -sf "$API_URL/api/v1/buildings/$BID/status" -H "$AUTH" | python3 "$HELPER" fault_status

log "Infeasible target"
curl -sf -X POST "$API_URL/api/v1/demo/scenarios/infeasible_target/start" -H "$AUTH" >/dev/null
curl -sf -X POST "$API_URL/api/v1/buildings/$BID/optimization/generate" -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"energy_weight":0.25,"cost_weight":0.2,"carbon_weight":0.2,"comfort_weight":0.2,"peak_weight":0.1,"equipment_weight":0.05,"energy_target_pct":40,"zero_comfort_deviation":true,"allow_schedule_changes":false}' \
  | python3 "$HELPER" infeasible

log "Assistant explanation"
curl -sf -X POST "$API_URL/api/v1/assistant/chat" -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d "{\"building_id\":\"$BID\",\"message\":\"Why is the system in Guarded Mode?\"}" \
  | python3 "$HELPER" assistant

log "Rollback to safe policy"
curl -sf -X POST "$API_URL/api/v1/buildings/$BID/rollback" -H "$AUTH" \
  -H 'Content-Type: application/json' \
  -d '{"reason":"Replay emergency rollback","target_safe_policy":"default_safe_policy"}' \
  | python3 "$HELPER" rollback

log "Ledger + audit evidence"
curl -sf "$API_URL/api/v1/buildings/$BID/ledger" -H "$AUTH" | python3 "$HELPER" ledger
curl -sf "$API_URL/api/v1/buildings/$BID/audit" -H "$AUTH" | python3 "$HELPER" audit

printf '\nReplay complete.\n'
printf 'Open the UI with: make demo\n'
printf '  Web http://localhost:3000\n'
printf '  API %s/docs\n' "$API_URL"
printf 'Login: manager@twinpilot.demo / TwinPilot-Manager-Demo!\n'
printf 'Optional LLM: make ollama   # then set AGENT_PROVIDER=ollama in .env\n'
