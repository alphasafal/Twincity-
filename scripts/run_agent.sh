#!/usr/bin/env bash
# Run the EnergyPlus AGENT closed-loop experiment (SafetyShield-gated setpoint overrides).
# Identical IDF / EPW / occupancy / period as run_baseline.sh — controller is the only difference.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export ENERGYPLUS_HOME="${ENERGYPLUS_HOME:-$ROOT/third_party/EnergyPlus}"
export ENERGYPLUS_MODEL_PATH="${ENERGYPLUS_MODEL_PATH:-$ROOT/building-models/sample-office/office_5zone.idf}"
export ENERGYPLUS_WEATHER_PATH="${ENERGYPLUS_WEATHER_PATH:-$ROOT/building-models/weather/chicago.epw}"
export RESULTS_AGENT_DIR="${RESULTS_AGENT_DIR:-$ROOT/results/agent}"
mkdir -p "$RESULTS_AGENT_DIR"

if [[ ! -x "$ENERGYPLUS_HOME/energyplus" && ! -f "$ENERGYPLUS_HOME/energyplus" ]]; then
  echo "ERROR: EnergyPlus binary not found at ENERGYPLUS_HOME=$ENERGYPLUS_HOME" >&2
  echo "Install via: ./scripts/setup_energyplus.sh" >&2
  exit 2
fi

PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi

export PYTHONPATH="$ROOT/services/simulator:$ROOT/services/optimizer:${PYTHONPATH:-}"

echo "==> Agent EnergyPlus experiment (deterministic agent + safety gate)"
echo "    IDF: $ENERGYPLUS_MODEL_PATH"
echo "    EPW: $ENERGYPLUS_WEATHER_PATH"
echo "    OUT: $RESULTS_AGENT_DIR"

"$PYTHON" - <<'PY'
import json, os, sys
from pathlib import Path
from twinpilot_simulator.ep_experiment import (
    ExperimentConfig,
    resolve_paths_from_env,
    run_experiment,
    EnergyPlusUnavailableError,
    EnergyPlusRunError,
)

out = Path(os.environ["RESULTS_AGENT_DIR"])
try:
    paths = resolve_paths_from_env(out)
    summary = run_experiment(ExperimentConfig(paths=paths, mode="agent"))
except (EnergyPlusUnavailableError, EnergyPlusRunError) as exc:
    print(f"AGENT FAILED: {exc}", file=sys.stderr)
    fail = {
        "simulation_status": "failed",
        "experiment": "agent",
        "error_message": str(exc),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "summary.json").write_text(json.dumps(fail, indent=2))
    sys.exit(1)

print(json.dumps({
    "simulation_status": summary["simulation_status"],
    "total_energy_kwh": summary["total_energy_kwh"],
    "hvac_energy_kwh": summary["hvac_energy_kwh"],
    "peak_power_kw": summary["peak_power_kw"],
    "carbon_estimate_kg": summary["carbon_estimate_kg"],
    "occupied_comfort_violation_hours": summary["occupied_comfort_violation_hours"],
    "action_counts": summary["action_counts"],
}, indent=2))
print(f"Wrote {out / 'summary.json'}")
PY
