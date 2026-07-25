#!/usr/bin/env bash
# Fresh-clone setup for TwinPilot / Eco-Loop evaluators.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "==> TwinPilot / Eco-Loop setup"

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

if [[ -x "$ROOT/infrastructure/scripts/setup.sh" ]]; then
  bash "$ROOT/infrastructure/scripts/setup.sh"
else
  python3 -m venv .venv
  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install -U pip
  pip install -e "$ROOT/services/optimizer" -e "$ROOT/services/simulator" -e "$ROOT/services/agent" -e "$ROOT/services/api"
  if command -v pnpm >/dev/null; then
    pnpm install
  fi
fi

echo "==> EnergyPlus (optional for mock demo; required for real closed-loop experiments)"
if [[ "${SKIP_ENERGYPLUS:-0}" != "1" ]]; then
  bash "$ROOT/scripts/setup_energyplus.sh" || {
    echo "WARNING: EnergyPlus install failed. Mock demo still works with SIMULATOR_PROVIDER=mock."
  }
fi

echo
echo "Setup complete."
echo "  Mock demo:     ./scripts/run_demo.sh"
echo "  Real E+ loop:  ./scripts/run_baseline.sh && ./scripts/run_agent.sh && ./scripts/compare_results.sh"
