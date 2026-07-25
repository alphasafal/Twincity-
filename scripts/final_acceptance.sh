#!/usr/bin/env bash
# Final acceptance orchestrator for Eco-Loop hackathon release.
# Safe, non-destructive: does not delete user files, push, or tag.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="${FINAL_ACCEPTANCE_DIR:-$ROOT/final-release/logs/acceptance-$TS}"
mkdir -p "$OUT_DIR" "$ROOT/final-release/logs"

SUMMARY="$OUT_DIR/SUMMARY.txt"
PASS=0
FAIL=0
WARN=0

log() { echo "$*" | tee -a "$SUMMARY"; }
phase() { log ""; log "======== PHASE: $* ========"; }

run_step() {
  local name="$1"; shift
  local logfile="$OUT_DIR/${name}.log"
  log "-- $name"
  local start end ec
  start=$(date +%s)
  set +e
  "$@" >"$logfile" 2>&1
  ec=$?
  set -e
  end=$(date +%s)
  if [[ $ec -eq 0 ]]; then
    log "   PASS ($((end-start))s) → $logfile"
    PASS=$((PASS+1))
  else
    log "   FAIL exit=$ec ($((end-start))s) → $logfile"
    FAIL=$((FAIL+1))
  fi
  return 0
}

PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3)"

log "Eco-Loop final acceptance"
log "UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
log "ROOT=$ROOT"
log "HEAD=$(git rev-parse HEAD 2>/dev/null || echo unknown)"
log "BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

phase "1 Repository state"
{
  git status --short
  git rev-parse HEAD
  git ls-files results submission-evidence
} >"$OUT_DIR/01-repo-state.log" 2>&1
if git ls-files results submission-evidence | rg -v '\.gitkeep$' >/dev/null 2>&1; then
  log "   FAIL — tracked generated results beyond .gitkeep"
  FAIL=$((FAIL+1))
else
  log "   PASS — only .gitkeep tracked under results/submission-evidence"
  PASS=$((PASS+1))
fi

phase "2 Prerequisites"
run_step "02-prerequisites" ./scripts/check_prerequisites.sh

phase "3 Automated tests (fast subset)"
if [[ -x "$PYTHON" ]]; then
  export PYTHONPATH="$ROOT/services/api:$ROOT/services/optimizer:$ROOT/services/simulator:$ROOT/services/agent:$ROOT/services/mcp-server:${PYTHONPATH:-}"
  run_step "03-pytest-core" "$PYTHON" -m pytest \
    services/simulator/tests services/optimizer/tests services/api/tests tests/integration \
    -q --tb=line
  run_step "03-pytest-safety" "$PYTHON" -m pytest \
    services/simulator/tests services/optimizer/tests \
    -q -k 'safety or SafetyShield or setpoint' --tb=line
else
  log "   WARN — python unavailable for pytest"
  WARN=$((WARN+1))
fi

phase "4 EnergyPlus setup + Path A experiments"
run_step "04-setup-energyplus" ./scripts/setup_energyplus.sh
run_step "04-baseline" ./scripts/run_baseline.sh
run_step "04-agent" ./scripts/run_agent.sh
run_step "04-compare" ./scripts/compare_results.sh

phase "5 Independent metrics / comfort / actions"
run_step "05-independent" "$PYTHON" - <<'PY'
import json
from pathlib import Path
from collections import Counter
b=json.loads(Path("results/baseline/summary.json").read_text())
a=json.loads(Path("results/agent/summary.json").read_text())
c=json.loads(Path("results/comparison/comparison.json").read_text())
acts=json.loads(Path("results/agent/actions.json").read_text())
assert b["simulation_status"]=="completed" and a["simulation_status"]=="completed"
bt,at=b["total_energy_kwh"],a["total_energy_kwh"]
bh,ah=b["hvac_energy_kwh"],a["hvac_energy_kwh"]
bp,ap=b["peak_power_kw"],a["peak_power_kw"]
ind_t=(bt-at)/bt*100
ind_h=(bh-ah)/bh*100
ind_p=(bp-ap)/bp*100
assert abs(ind_t-c["total_energy_kwh"]["percent_reduction"])<1e-3
assert abs(ind_h-c["hvac_energy_kwh"]["percent_reduction"])<1e-3
assert abs(ind_p-c["peak_power_kw"]["percent_reduction"])<1e-3
assert float(a["occupied_comfort_violation_hours"])==0.0
assert float(a["occupied_comfort_degree_hours"])==0.0
cnt=Counter(x["disposition"] for x in acts)
assert cnt.get("approved",0)==a["action_counts"]["approved"]
assert sum(1 for x in acts if x.get("energyplus_actuator_written") is True) >= 5
print(json.dumps({"ind_t":ind_t,"ind_h":ind_h,"ind_p":ind_p,"actions":dict(cnt)},indent=2))
PY

phase "6 MCP / Ollama experiment"
# Keep artifacts under results/llm_mcp; do not use leaked cleanroom env
unset RESULTS_LLM_DIR TWINPILOT_MCP_TRACE TWINPILOT_MCP_EVIDENCE_DIR || true
export RESULTS_LLM_DIR="$ROOT/results/llm_mcp"
export TWINPILOT_MCP_TRACE="$OUT_DIR/mcp-runtime-trace.jsonl"
run_step "06-llm-mcp" ./scripts/run_llm_mcp_experiment.sh
run_step "06-mcp-pids" "$PYTHON" - <<'PY'
import json
from pathlib import Path
s=json.loads(Path("results/llm_mcp/summary.json").read_text())
assert s.get("mcp_transport")=="stdio"
assert s.get("mcp_pids_differ") is True
assert s.get("mcp_client_pid") != s.get("mcp_server_pid")
assert s.get("llm_bypass_possible") is False
print(s)
PY

phase "7 Safety rejection + Ollama fallback"
run_step "07-safety-35c" "$PYTHON" - <<'PY'
import json
from pathlib import Path
rows=[json.loads(l) for l in Path("results/llm_mcp/stage_log.jsonl").read_text().splitlines() if l.strip()]
s=next(r for r in rows if r.get("stage")=="safety_shield_rejects_unsafe")
assert s.get("approved") is False and s.get("disposition")=="rejected"
assert 35.0 == float(s.get("proposed"))
print(s)
PY

FALLBACK_DIR="$OUT_DIR/ollama-fallback"
mkdir -p "$FALLBACK_DIR"
run_step "07-ollama-fallback" env \
  OLLAMA_BASE_URL=http://127.0.0.1:1 \
  RESULTS_LLM_DIR="$FALLBACK_DIR" \
  TWINPILOT_MCP_TRACE="$FALLBACK_DIR/mcp-trace.jsonl" \
  ./scripts/run_llm_mcp_experiment.sh
run_step "07-fallback-counts" "$PYTHON" - <<PY
import json
from pathlib import Path
from collections import Counter
root=Path("$FALLBACK_DIR")
s=json.loads((root/"summary.json").read_text())
acts=json.loads((root/"agent"/"actions.json").read_text())
cnt=Counter(a.get("disposition") for a in acts)
assert cnt.get("fallback",0) == 48 or (s.get("agent",{}).get("action_counts") or {}).get("fallback",0)==48
print({"dispositions":dict(cnt),"summary":s.get("agent",{}).get("action_counts")})
PY

phase "8 Submission evidence build"
run_step "08-build-evidence" "$PYTHON" scripts/build_submission_evidence.py

phase "9 Tracked-results guard"
run_step "09-no-tracked-results" bash -c '
  bad=$(git ls-files results submission-evidence | grep -v gitkeep || true)
  if [[ -n "$bad" ]]; then echo "$bad"; exit 1; fi
  echo OK
'

phase "10 Final summary"
STATUS="PASS"
[[ $FAIL -eq 0 ]] || STATUS="FAIL"
log ""
log "OVERALL_STATUS=$STATUS"
log "PASS_STEPS=$PASS FAIL_STEPS=$FAIL WARN_STEPS=$WARN"
log "ARTIFACT_DIR=$OUT_DIR"
log "NOTE: This script does not push, tag, or delete user data."

# Also mirror short summary into final-release/logs
cp "$SUMMARY" "$ROOT/final-release/logs/final-acceptance-latest.txt"

if [[ "$STATUS" != "PASS" ]]; then
  exit 1
fi
exit 0
