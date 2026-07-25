#!/usr/bin/env bash
# Check EnergyPlus configuration and adapter readiness.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate" 2>/dev/null || true

export ENERGYPLUS_HOME="${ENERGYPLUS_HOME:-$ROOT/third_party/EnergyPlus}"
export ENERGYPLUS_MODEL_PATH="${ENERGYPLUS_MODEL_PATH:-$ROOT/building-models/sample-office/office_5zone.idf}"
export ENERGYPLUS_WEATHER_PATH="${ENERGYPLUS_WEATHER_PATH:-$ROOT/building-models/weather/chicago.epw}"
export PYTHONPATH="$ROOT/services/simulator:$ROOT/services/optimizer:${PYTHONPATH:-}"

echo "==> TwinPilot EnergyPlus check"
echo "ENERGYPLUS_HOME=$ENERGYPLUS_HOME"
echo "ENERGYPLUS_MODEL_PATH=$ENERGYPLUS_MODEL_PATH"
echo "ENERGYPLUS_WEATHER_PATH=$ENERGYPLUS_WEATHER_PATH"
echo "SIMULATOR_PROVIDER=${SIMULATOR_PROVIDER:-mock}"
echo "ENERGYPLUS_ALLOW_MOCK_FALLBACK=${ENERGYPLUS_ALLOW_MOCK_FALLBACK:-0}"

python - <<'PY'
import os
import sys

home = os.getenv("ENERGYPLUS_HOME")
model = os.getenv("ENERGYPLUS_MODEL_PATH")
weather = os.getenv("ENERGYPLUS_WEATHER_PATH")
ok = True

if not home or not os.path.isdir(home):
    print(f"ERROR: ENERGYPLUS_HOME missing: {home}")
    ok = False
elif not os.path.exists(os.path.join(home, "energyplus")):
    print(f"ERROR: energyplus binary not found under {home}")
    ok = False
else:
    print(f"OK: ENERGYPLUS_HOME ({home})")

if not model or not os.path.isfile(model):
    print(f"ERROR: model missing: {model}")
    ok = False
else:
    print(f"OK: model {model}")

if not weather or not os.path.isfile(weather):
    print(f"ERROR: weather missing: {weather}")
    ok = False
else:
    print(f"OK: weather {weather}")

if not ok:
    print("\nRun ./scripts/setup_energyplus.sh and ensure building-models assets exist.")
    print("UI demo can still use SIMULATOR_PROVIDER=mock.")
    sys.exit(1)

from twinpilot_simulator.energyplus import EnergyPlusAdapter
from twinpilot_simulator.base import SimulationConfig
from twinpilot_simulator.ep_experiment import EnergyPlusUnavailableError

adapter = EnergyPlusAdapter()
try:
    state = adapter.initialize(
        SimulationConfig(
            energyplus_home=home,
            model_path=model,
            weather_path=weather,
        )
    )
except EnergyPlusUnavailableError as exc:
    print(f"ERROR: strict adapter init failed: {exc}")
    sys.exit(1)

health = adapter.health()
print("Adapter health:", health)
print("State.simulated:", state.simulated)
if state.simulated:
    print("ERROR: expected simulated=False for EnergyPlus path")
    sys.exit(1)
print("\nEnergyPlus check PASSED")
sys.exit(0)
PY
