#!/usr/bin/env bash
# Optional: install Ollama + pull a small open model for TwinPilot assistant.
# TwinPilot works WITHOUT this (deterministic agent is default).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
MODEL="${OLLAMA_MODEL:-llama3.2:1b}"

echo "TwinPilot optional Ollama setup"
echo "Model: $MODEL"
echo "Note: demo mode uses AGENT_PROVIDER=deterministic by default."

if ! command -v ollama >/dev/null 2>&1; then
  echo "Ollama not found. Installing via official script..."
  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required to install Ollama"
    exit 1
  fi
  curl -fsSL https://ollama.com/install.sh | sh
fi

# Start server if needed
if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
  echo "Starting ollama serve in background..."
  nohup ollama serve >/tmp/ollama-twinpilot.log 2>&1 &
  for i in $(seq 1 30); do
    if curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

echo "Pulling model $MODEL (this may take several minutes)..."
ollama pull "$MODEL"

if [[ -f "$ROOT/.env" ]]; then
  if grep -q '^AGENT_PROVIDER=' "$ROOT/.env"; then
    sed -i 's/^AGENT_PROVIDER=.*/AGENT_PROVIDER=ollama/' "$ROOT/.env"
  else
    echo 'AGENT_PROVIDER=ollama' >> "$ROOT/.env"
  fi
  if grep -q '^OLLAMA_MODEL=' "$ROOT/.env"; then
    sed -i "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=$MODEL|" "$ROOT/.env"
  else
    echo "OLLAMA_MODEL=$MODEL" >> "$ROOT/.env"
  fi
  if grep -q '^OLLAMA_BASE_URL=' "$ROOT/.env"; then
    sed -i 's|^OLLAMA_BASE_URL=.*|OLLAMA_BASE_URL=http://127.0.0.1:11434|' "$ROOT/.env"
  else
    echo 'OLLAMA_BASE_URL=http://127.0.0.1:11434' >> "$ROOT/.env"
  fi
fi

echo ""
echo "Ollama ready."
echo "  Restart API (make demo) to use AGENT_PROVIDER=ollama"
echo "  Or keep deterministic agent — no model required."
