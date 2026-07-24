#!/usr/bin/env bash
# Check EnergyPlus configuration and adapter readiness (optional dependency).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate" 2>/dev/null || true

echo "==> TwinPilot EnergyPlus check"
echo "ENERGYPLUS_HOME=${ENERGYPLUS_HOME:-<unset>}"
echo "ENERGYPLUS_MODEL_PATH=${ENERGYPLUS_MODEL_PATH:-<unset>}"
echo "ENERGYPLUS_WEATHER_PATH=${ENERGYPLUS_WEATHER_PATH:-<unset>}"
echo "SIMULATOR_PROVIDER=${SIMULATOR_PROVIDER:-mock}"

python - <<'PY'
import os
import sys

home = os.getenv("ENERGYPLUS_HOME")
model = os.getenv("ENERGYPLUS_MODEL_PATH")
weather = os.getenv("ENERGYPLUS_WEATHER_PATH")

ok = True
if not home:
    print("WARN: ENERGYPLUS_HOME not set — adapter will use mock fallback")
    ok = False
elif not os.path.isdir(home):
    print(f"WARN: ENERGYPLUS_HOME does not exist: {home}")
    ok = False
else:
    print(f"OK: ENERGYPLUS_HOME exists ({home})")

if not model or not os.path.isfile(model):
    print("WARN: ENERGYPLUS_MODEL_PATH missing or not a file")
    print("      Place a sample IDF under building-models/sample-office/ (see README there)")
    ok = False
else:
    print(f"OK: model path {model}")

if not weather or not os.path.isfile(weather):
    print("WARN: ENERGYPLUS_WEATHER_PATH missing or not a file")
    print("      Place EPW weather under building-models/weather/ (see README there)")
    ok = False
else:
    print(f"OK: weather path {weather}")

try:
    from twinpilot_simulator.energyplus import EnergyPlusAdapter
    from twinpilot_simulator.base import SimulationConfig

    adapter = EnergyPlusAdapter()
    cfg = SimulationConfig(
        energyplus_home=home,
        model_path=model,
        weather_path=weather,
    )
    state = adapter.initialize(cfg)
    health = adapter.health()
    print("Adapter health:", health)
    print("State.simulated:", getattr(state, "simulated", None))
except Exception as exc:
    print(f"Adapter import/init failed: {exc}")
    ok = False

if ok:
    print("\nEnergyPlus appears configured. Full co-simulation still depends on local EnergyPlus Python bindings.")
    sys.exit(0)
else:
    print("\nEnergyPlus is OPTIONAL. Default SIMULATOR_PROVIDER=mock is sufficient for the demo.")
    sys.exit(0)
PY
