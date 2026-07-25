#!/usr/bin/env bash
# Path C — hybrid supervisory experiment:
# EnergyPlus → MCP stdio → Ollama strategy → deterministic optimiser → SafetyShield → actuator
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export ENERGYPLUS_HOME="${ENERGYPLUS_HOME:-$ROOT/third_party/EnergyPlus}"
export ENERGYPLUS_MODEL_PATH="${ENERGYPLUS_MODEL_PATH:-$ROOT/building-models/sample-office/office_5zone.idf}"
export ENERGYPLUS_WEATHER_PATH="${ENERGYPLUS_WEATHER_PATH:-$ROOT/building-models/weather/chicago.epw}"
export RESULTS_HYBRID_DIR="${RESULTS_HYBRID_DIR:-$ROOT/results/hybrid}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:1b}"
export TWINPILOT_MCP_TRACE="${TWINPILOT_MCP_TRACE:-$RESULTS_HYBRID_DIR/mcp-runtime-trace.jsonl}"
mkdir -p "$RESULTS_HYBRID_DIR"

PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3)"
export PYTHONPATH="$ROOT/services/simulator:$ROOT/services/optimizer:$ROOT/services/agent:$ROOT/services/mcp-server:${PYTHONPATH:-}"

echo "==> Hybrid supervisory Path C (LLM strategy + deterministic optimiser + SafetyShield)"
echo "    OUT: $RESULTS_HYBRID_DIR"
"$PYTHON" "$ROOT/scripts/hybrid_supervisory_loop.py"
