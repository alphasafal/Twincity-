#!/usr/bin/env bash
# Fast pre-demo smoke test. Non-destructive. Does not push/tag.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "== Eco-Loop final smoke test =="
echo "UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "HEAD=$(git rev-parse HEAD)"
echo "BRANCH=$(git rev-parse --abbrev-ref HEAD)"

fail=0
check() {
  local name="$1"; shift
  if "$@"; then
    echo "PASS  $name"
  else
    echo "FAIL  $name"
    fail=1
  fi
}

check "prerequisites" ./scripts/check_prerequisites.sh

PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3)"

check "baseline summary present or runnable" bash -c '
  if [[ -f results/baseline/summary.json ]]; then
    python3 -c "import json; s=json.load(open(\"results/baseline/summary.json\")); assert s.get(\"simulation_status\")==\"completed\""
  else
    ./scripts/run_baseline.sh
  fi
'

check "agent summary present or runnable" bash -c '
  if [[ -f results/agent/summary.json ]]; then
    python3 -c "import json; s=json.load(open(\"results/agent/summary.json\")); assert s.get(\"simulation_status\")==\"completed\"; assert s[\"action_counts\"][\"approved\"]>=1"
  else
    ./scripts/run_agent.sh
  fi
'

check "comparison present or runnable" bash -c '
  if [[ -f results/comparison/comparison.json ]]; then
    true
  else
    ./scripts/compare_results.sh
  fi
'

check "comfort zero on agent" "$PYTHON" -c '
import json
a=json.load(open("results/agent/summary.json"))
assert float(a["occupied_comfort_violation_hours"])==0.0
assert float(a["occupied_comfort_degree_hours"])==0.0
print("comfort ok")
'

check "actuator writes exist" "$PYTHON" -c '
import json
acts=json.load(open("results/agent/actions.json"))
assert sum(1 for a in acts if a.get("energyplus_actuator_written") is True) >= 5
print("actuator ok", len(acts))
'

check "no tracked generated results" bash -c '
  bad=$(git ls-files results submission-evidence | grep -v gitkeep || true)
  test -z "$bad"
'

check "ollama healthy" bash -c 'curl -sf http://127.0.0.1:11434/api/tags >/dev/null'

check "stdio MCP session opens" "$PYTHON" - <<'PY'
import sys
from pathlib import Path
sys.path[:0]=["services/mcp-server"]
from twinpilot_mcp.stdio_session import open_energyplus_mcp_session
s=open_energyplus_mcp_session(timeout_s=15.0)
try:
    assert s.initialized
    assert s.server_pid and s.server_pid != s.client_pid
    tools=s.list_tools()
    assert tools
    print({"client":s.client_pid,"server":s.server_pid,"tools":len(tools)})
finally:
    s.close()
PY

check "dashboard/API reachable or documented offline" bash -c '
  if curl -sf http://127.0.0.1:8000/health >/dev/null; then
    echo "API health ok"
  else
    echo "WARN API not running — start with DATA_MODE=energyplus ./scripts/run_demo.sh"
    # soft warning only for smoke
    true
  fi
'

if [[ $fail -ne 0 ]]; then
  echo "SMOKE RESULT: FAIL"
  exit 1
fi
echo "SMOKE RESULT: PASS"
exit 0
