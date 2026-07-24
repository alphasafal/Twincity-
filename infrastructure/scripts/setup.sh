#!/usr/bin/env bash
# TwinPilot local setup — Python venv + editable packages + pnpm install
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

echo "==> TwinPilot setup"

if [[ ! -d "$ROOT/.venv" ]]; then
  echo "Creating Python virtualenv at .venv"
  python3 -m venv "$ROOT/.venv"
fi

# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate"
python -m pip install --upgrade pip

echo "Installing Python packages (optimizer, simulator, agent, api, mcp-server)"
pip install -e "$ROOT/services/optimizer"
pip install -e "$ROOT/services/simulator"
pip install -e "$ROOT/services/agent"
pip install -e "$ROOT/services/api"
pip install -e "$ROOT/services/api[dev]" 2>/dev/null || pip install pytest pytest-asyncio ruff
pip install -e "$ROOT/services/mcp-server" 2>/dev/null || true

if [[ ! -f "$ROOT/.env" ]]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo "Wrote .env from .env.example"
fi

if [[ ! -f "$ROOT/apps/web/.env.local" ]]; then
  cp "$ROOT/apps/web/.env.local.example" "$ROOT/apps/web/.env.local"
  echo "Wrote apps/web/.env.local"
fi

if command -v pnpm >/dev/null 2>&1; then
  echo "Installing JS workspace deps (pnpm)"
  pnpm install
else
  echo "WARN: pnpm not found — install Node 22+ and enable corepack, then re-run setup"
fi

echo ""
echo "Setup complete."
echo "  Demo:  make demo"
echo "  API:   make api"
echo "  Web:   make web"
echo "  Tests: make test"
