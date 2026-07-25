#!/usr/bin/env bash
# Internal helper for final-release clean-clone verification. Non-destructive to source repo.
set -euo pipefail

SRC="${1:-/workspace}"
CLONE="${2:-/tmp/ecolooop-clean-clone-$(date -u +%Y%m%dT%H%M%SZ)}"
LOG="${3:-$SRC/final-release/logs/clean-clone.log}"

exec > >(tee "$LOG") 2>&1

echo "START_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "SRC=$SRC"
echo "CLONE=$CLONE"
cd "$SRC"
echo "SOURCE_HEAD=$(git rev-parse HEAD)"
echo "SOURCE_BRANCH=$(git rev-parse --abbrev-ref HEAD)"

rm -rf "$CLONE"
git clone --local "$SRC" "$CLONE"

# Bring uncommitted script/test fixes that are part of the release candidate working tree
cp -a "$SRC/scripts/." "$CLONE/scripts/"
cp -a "$SRC/tests/integration/test_control_flow.py" "$CLONE/tests/integration/test_control_flow.py"

cd "$CLONE"

echo "== JSON count at clone (should be 0 under results) =="
find results -name '*.json' 2>/dev/null | wc -l || true

# Reuse EnergyPlus binary via symlink if needed (large dependency)
mkdir -p third_party
if [[ ! -x third_party/EnergyPlus/energyplus && -x /workspace/third_party/EnergyPlus/energyplus ]]; then
  ln -sfn /workspace/third_party/EnergyPlus third_party/EnergyPlus
fi

# Fresh venv for honesty of clean clone python deps
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -U pip wheel >/dev/null
  ./scripts/setup.sh || true
else
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

[[ -f .env ]] || cp .env.example .env
if grep -q '^DATA_MODE=' .env; then
  sed -i 's/^DATA_MODE=.*/DATA_MODE=energyplus/' .env
else
  echo 'DATA_MODE=energyplus' >> .env
fi

export ENERGYPLUS_HOME="${ENERGYPLUS_HOME:-$CLONE/third_party/EnergyPlus}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:1b}"
unset RESULTS_LLM_DIR TWINPILOT_MCP_TRACE TWINPILOT_MCP_EVIDENCE_DIR || true

echo "== check_prerequisites =="
./scripts/check_prerequisites.sh

echo "== setup_energyplus =="
./scripts/setup_energyplus.sh

echo "== run_baseline =="
./scripts/run_baseline.sh

echo "== run_agent =="
./scripts/run_agent.sh

echo "== compare_results =="
./scripts/compare_results.sh

echo "== run_llm_mcp_experiment =="
./scripts/run_llm_mcp_experiment.sh

echo "== build_submission_evidence =="
python scripts/build_submission_evidence.py

echo "== dashboard payload no-data / real-data =="
python "$SRC/scripts/_final_clean_clone_dashboard_check.py"

echo "END_UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "CLONE_DONE=$CLONE"
echo "CLEAN_CLONE_STATUS=PASS"
