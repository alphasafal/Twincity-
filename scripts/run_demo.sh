#!/usr/bin/env bash
# Start the local mock-twin demo (API + web). Does not claim EnergyPlus closed-loop.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export SIMULATOR_PROVIDER="${SIMULATOR_PROVIDER:-mock}"
export AGENT_PROVIDER="${AGENT_PROVIDER:-deterministic}"

echo "Starting TwinPilot demo (SIMULATOR_PROVIDER=$SIMULATOR_PROVIDER)"
echo "For EnergyPlus experiments use ./scripts/run_baseline.sh / run_agent.sh instead."
exec bash "$ROOT/infrastructure/scripts/demo.sh"
