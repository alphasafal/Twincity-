#!/usr/bin/env bash
# Verify local prerequisites for Eco-Loop EnergyPlus + stdio MCP + Ollama experiments.
# Prints PASS/FAIL lines. Exits non-zero if any mandatory check fails.
# Does not print secret values.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

FAILS=0
pass() { echo "PASS  $*"; }
fail() { echo "FAIL  $*"; FAILS=$((FAILS + 1)); }
warn() { echo "WARN  $*"; }

echo "== Eco-Loop prerequisite check =="
echo "root=$ROOT"
echo "time=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# OS / arch
OS_NAME="$(uname -s 2>/dev/null || echo unknown)"
ARCH="$(uname -m 2>/dev/null || echo unknown)"
if [[ "$OS_NAME" == "Linux" || "$OS_NAME" == "Darwin" ]]; then
  pass "OS compatible ($OS_NAME)"
else
  fail "OS unsupported for documented workflow ($OS_NAME)"
fi
if [[ "$ARCH" == "x86_64" || "$ARCH" == "amd64" || "$ARCH" == "arm64" || "$ARCH" == "aarch64" ]]; then
  pass "CPU architecture ($ARCH)"
else
  fail "CPU architecture not in supported set ($ARCH)"
fi

# Python
if command -v python3 >/dev/null 2>&1; then
  PY_VER="$(python3 -c 'import sys; print("%d.%d.%d"%sys.version_info[:3])')"
  PY_MAJOR="$(python3 -c 'import sys; print(sys.version_info[0])')"
  PY_MINOR="$(python3 -c 'import sys; print(sys.version_info[1])')"
  if [[ "$PY_MAJOR" -gt 3 || ( "$PY_MAJOR" -eq 3 && "$PY_MINOR" -ge 11 ) ]]; then
    pass "Python >=3.11 ($PY_VER)"
  else
    fail "Python >=3.11 required (found $PY_VER)"
  fi
else
  fail "python3 not found"
fi

# Node / pnpm
if command -v node >/dev/null 2>&1; then
  NODE_VER="$(node -v | tr -d v)"
  NODE_MAJOR="${NODE_VER%%.*}"
  if [[ "$NODE_MAJOR" -ge 20 ]]; then
    pass "Node.js >=20 (v$NODE_VER)"
  else
    fail "Node.js >=20 required (found v$NODE_VER)"
  fi
else
  fail "node not found"
fi
if command -v pnpm >/dev/null 2>&1; then
  pass "pnpm available ($(pnpm -v))"
else
  fail "pnpm not found (required for web demo)"
fi

# EnergyPlus
EP_HOME="${ENERGYPLUS_HOME:-$ROOT/third_party/EnergyPlus}"
EP_BIN="$EP_HOME/energyplus"
if [[ -x "$EP_BIN" ]]; then
  EP_VER="$("$EP_BIN" --version 2>/dev/null | head -1 || true)"
  pass "EnergyPlus executable ($EP_BIN)"
  if echo "$EP_VER" | grep -q "24.1"; then
    pass "EnergyPlus version ($EP_VER)"
  else
    warn "EnergyPlus version string unexpected: ${EP_VER:-unknown} (docs expect 24.1.x)"
  fi
else
  fail "EnergyPlus missing at $EP_BIN — run ./scripts/setup_energyplus.sh"
fi

IDF="${ENERGYPLUS_MODEL_PATH:-$ROOT/building-models/sample-office/office_5zone.idf}"
EPW="${ENERGYPLUS_WEATHER_PATH:-$ROOT/building-models/weather/chicago.epw}"
if [[ -f "$IDF" ]]; then pass "IDF present ($IDF)"; else fail "IDF missing ($IDF)"; fi
if [[ -f "$EPW" ]]; then pass "EPW present ($EPW)"; else fail "EPW missing ($EPW)"; fi

# Writable results
mkdir -p "$ROOT/results"
if [[ -w "$ROOT/results" ]]; then
  pass "results/ is writable"
else
  fail "results/ is not writable"
fi

# Ports (advisory)
for PORT in 8000 3000 11434; do
  if command -v lsof >/dev/null 2>&1 && lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    warn "port $PORT is already in use"
  else
    pass "port $PORT appears free (or lsof unavailable to confirm)"
  fi
done

# Env config names only
if [[ -f "$ROOT/.env" ]]; then
  pass ".env exists (values not printed)"
else
  warn ".env missing — ./scripts/setup.sh copies from .env.example"
fi
if grep -q '^DATA_MODE=' "$ROOT/.env.example" 2>/dev/null; then
  pass ".env.example defines DATA_MODE"
else
  fail ".env.example missing DATA_MODE"
fi

# Ollama
if command -v ollama >/dev/null 2>&1; then
  pass "Ollama executable ($(ollama --version 2>/dev/null | head -1 || echo present))"
else
  fail "Ollama executable not found — install from https://ollama.com"
fi

OLLAMA_URL="${OLLAMA_BASE_URL:-http://127.0.0.1:11434}"
MODEL="${OLLAMA_MODEL:-llama3.2:1b}"
if curl -sf "$OLLAMA_URL/api/tags" >/dev/null 2>&1; then
  pass "Ollama server healthy ($OLLAMA_URL)"
  if curl -sf "$OLLAMA_URL/api/tags" | python3 -c "import sys,json; m=json.load(sys.stdin); names=[x.get('name','') for x in m.get('models',[])]; raise SystemExit(0 if any(n=='$MODEL' or n.startswith('$MODEL') for n in names) else 1)"; then
    pass "Required model present ($MODEL)"
  else
    fail "Required model missing ($MODEL). Install with: ollama pull $MODEL"
  fi
else
  fail "Ollama server not healthy at $OLLAMA_URL — start with: ollama serve"
  fail "Cannot verify model $MODEL until server is healthy. Install later with: ollama pull $MODEL"
fi

# MCP package import
if PYTHONPATH="$ROOT/services/mcp-server:${PYTHONPATH:-}" python3 -c "import mcp, twinpilot_mcp" 2>/dev/null; then
  pass "MCP SDK + twinpilot_mcp importable"
else
  fail "MCP SDK / twinpilot_mcp import failed — run ./scripts/setup.sh"
fi

echo
if [[ "$FAILS" -gt 0 ]]; then
  echo "RESULT: FAIL ($FAILS mandatory check(s) failed)"
  exit 1
fi
echo "RESULT: PASS"
exit 0
