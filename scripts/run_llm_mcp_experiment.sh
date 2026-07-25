#!/usr/bin/env bash
# LLM + stdio MCP closed-loop experiment path with stage logs.
# EnergyPlus → MCP client → stdio → separate MCP server → tools → Ollama → SafetyShield → actuator
# Deterministic controller is the fallback when Ollama/MCP is unavailable.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export ENERGYPLUS_HOME="${ENERGYPLUS_HOME:-$ROOT/third_party/EnergyPlus}"
export ENERGYPLUS_MODEL_PATH="${ENERGYPLUS_MODEL_PATH:-$ROOT/building-models/sample-office/office_5zone.idf}"
export ENERGYPLUS_WEATHER_PATH="${ENERGYPLUS_WEATHER_PATH:-$ROOT/building-models/weather/chicago.epw}"
export RESULTS_LLM_DIR="${RESULTS_LLM_DIR:-$ROOT/results/llm_mcp}"
export OLLAMA_BASE_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
export OLLAMA_MODEL="${OLLAMA_MODEL:-llama3.2:1b}"
mkdir -p "$RESULTS_LLM_DIR"

PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
[[ -x "$PYTHON" ]] || PYTHON="$(command -v python3)"
export PYTHONPATH="$ROOT/services/simulator:$ROOT/services/optimizer:$ROOT/services/agent:$ROOT/services/mcp-server:${PYTHONPATH:-}"

"$PYTHON" "$ROOT/scripts/llm_mcp_loop.py"
