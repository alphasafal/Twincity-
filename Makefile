# TwinPilot developer Makefile
.PHONY: setup dev seed demo test energyplus-check lint web api mobile replay ollama help

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
VENV := $(ROOT)/.venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
API_DIR := $(ROOT)/services/api

help:
	@echo "TwinPilot targets:"
	@echo "  make setup            Install Python + JS deps, copy env examples"
	@echo "  make seed             Ensure demo DB seed (via API lifespan or script)"
	@echo "  make demo             Start API + web for local demo"
	@echo "  make dev              Parallel API + web (same as demo)"
	@echo "  make api              Run FastAPI only"
	@echo "  make web              Run Next.js only"
	@echo "  make mobile           Run Expo mobile"
	@echo "  make test             Run API pytest + web typecheck/lint"
	@echo "  make lint             Ruff (API) + web lint"
	@echo "  make energyplus-check Check EnergyPlus env / adapter readiness"
	@echo "  make replay           API end-to-end scenario replay (no UI required)"
	@echo "  make ollama           Optional: install Ollama + pull small model"

setup:
	@bash $(ROOT)/infrastructure/scripts/setup.sh

seed:
	@bash $(ROOT)/infrastructure/scripts/seed.sh

demo:
	@bash $(ROOT)/infrastructure/scripts/demo.sh

dev: demo

api:
	@cd $(API_DIR) && $(PYTHON) -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

web:
	@cd $(ROOT) && pnpm --filter @twinpilot/web dev

mobile:
	@cd $(ROOT) && pnpm --filter @twinpilot/mobile start

test:
	@cd $(API_DIR) && $(PYTHON) -m pytest -q
	@cd $(ROOT)/tests/integration && PYTHONPATH=$(API_DIR):$(ROOT)/services/optimizer:$(ROOT)/services/simulator:$(ROOT)/services/agent $(PYTHON) -m pytest -q
	@cd $(ROOT) && pnpm --filter @twinpilot/web typecheck
	@cd $(ROOT) && pnpm --filter @twinpilot/web lint

lint:
	@cd $(API_DIR) && $(VENV)/bin/ruff check app tests || $(PYTHON) -m ruff check app tests
	@cd $(ROOT) && pnpm --filter @twinpilot/web lint

energyplus-check:
	@bash $(ROOT)/infrastructure/scripts/energyplus-check.sh

replay:
	@bash $(ROOT)/infrastructure/scripts/replay.sh

ollama:
	@bash $(ROOT)/infrastructure/scripts/setup-ollama.sh

.PHONY: run-baseline run-agent compare-results energyplus-experiments
run-baseline:
	@bash $(ROOT)/scripts/run_baseline.sh
run-agent:
	@bash $(ROOT)/scripts/run_agent.sh
compare-results:
	@bash $(ROOT)/scripts/compare_results.sh
energyplus-experiments: run-baseline run-agent compare-results
