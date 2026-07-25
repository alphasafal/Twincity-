#!/usr/bin/env bash
# Multi-scenario baseline vs agent evaluation (identical inputs within each scenario).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
export ENERGYPLUS_HOME="${ENERGYPLUS_HOME:-$ROOT/third_party/EnergyPlus}"
export ENERGYPLUS_WEATHER_PATH="${ENERGYPLUS_WEATHER_PATH:-$ROOT/building-models/weather/chicago.epw}"
PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3)"
export PYTHONPATH="$ROOT/services/simulator:$ROOT/services/optimizer:${PYTHONPATH:-}"
"$PYTHON" "$ROOT/scripts/run_scenarios.py"
