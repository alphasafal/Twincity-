# TwinPilot — Eco-Loop Building Agents

**Verifiable autonomous building optimization** for an **EnergyPlus digital building** (not a physical BMS), with a measured closed-loop experiment path and an independent Safety Shield.

> Observe → propose → SafetyShield validates → EnergyPlus actuator executes → results are auditable.

---

## Problem statement

Buildings waste energy when HVAC setpoints ignore occupancy, weather, and comfort constraints. Fully autonomous LLM control is unsafe. Operators need a closed loop that is **measurable**, **reproducible**, and **hard-gated** by deterministic safety rules.

## Proposed solution

TwinPilot / Eco-Loop separates **proposal** from **actuation**:

1. Observe building state (EnergyPlus Runtime API, or an explicit mock twin)
2. Optionally package observations through a **separate local MCP server over stdio**
3. Agent (deterministic or Ollama) proposes a cooling-setpoint adjustment
4. Deterministic Safety Shield validates range, rate, deadband, sensors, and infrastructure health
5. Only approved actions are written to the EnergyPlus `Clg-SetP-Sch` schedule actuator (or mock apply)
6. Baseline vs agent experiments quantify energy, peak, comfort, and carbon *estimates*

## Architecture

```text
Web / Mobile ──► FastAPI RuntimeHub ──► Mock twin (only when DATA_MODE=mock)
                         │
                         ├── Optimizer + SafetyShield
                         └── Agent (deterministic | Ollama)

Measured EnergyPlus path:
  scripts/run_baseline.sh | run_agent.sh
    → ep_experiment (pyenergyplus Runtime API)
    → results/{baseline,agent,comparison}/   (generated locally; not committed)

LLM + MCP path (optional):
  EnergyPlus observation
    → MCP client (this process)
    → stdio transport
    → separate MCP server process (`python -m twinpilot_mcp`)
    → MCP tools (get_building_observation, …)
    → Ollama structured proposal (local)
    → SafetyShield (authoritative gate)
    → EnergyPlus actuator
```

**Layering (do not conflate):**

| Layer | Role |
|-------|------|
| MCP stdio transport | Moves observations/context between client and a **separate** MCP server process |
| Ollama | Local LLM reasoning only — never writes actuators |
| SafetyShield | Deterministic accept/reject/fallback before actuation |
| EnergyPlus Runtime API | Observations + `Clg-SetP-Sch` actuator writes |

Details: [docs/architecture.md](docs/architecture.md) · Audit map: [docs/audit/repository-map.md](docs/audit/repository-map.md)

## Technologies

| Layer | Stack |
|-------|--------|
| API | FastAPI, SQLAlchemy, JWT |
| Optimizer / Safety | `twinpilot-optimizer` |
| Simulator | Mock twin · EnergyPlus 24.1 Runtime API |
| Agent | Deterministic (default) · Ollama (optional, **local**) |
| Web | Next.js 15, React 19, Tailwind |
| Mobile | Expo 52 |
| MCP | `twinpilot-mcp` over **stdio** (separate process) |
| Experiments | `scripts/run_*.sh` → generated JSON under `results/` |

## Installation

```bash
./scripts/setup.sh                 # Python venv, packages, pnpm, .env
./scripts/setup_energyplus.sh      # EnergyPlus 24.1 → third_party/EnergyPlus
./scripts/check_prerequisites.sh   # OS, EnergyPlus, Ollama, model, ports, …
```

Or: `make setup`. Copy `.env.example` → `.env` (done by setup).

**Versions:** Python ≥3.11, Node 20+/22 (see `.nvmrc`), pnpm 10, EnergyPlus 24.1.0.

### Local Ollama prerequisite (LLM path)

The LLM/MCP experiment requires a **local** Ollama daemon and model (not a remote hosted API):

```bash
ollama serve                    # if not already running
ollama pull llama3.2:1b
export OLLAMA_BASE_URL=http://127.0.0.1:11434
export OLLAMA_MODEL=llama3.2:1b
```

`./scripts/check_prerequisites.sh` fails if Ollama or the model is missing — it will not claim Ollama testing passed.

## Demo procedure

### 0) Prerequisites

```bash
./scripts/check_prerequisites.sh
```

### A) Measured EnergyPlus closed loop (deterministic controller)

```bash
./scripts/run_baseline.sh
./scripts/run_agent.sh
./scripts/compare_results.sh
# → results/comparison/comparison.json  (freshly generated; not shipped in git)
```

### B) Dashboard (`DATA_MODE=energyplus`)

```bash
DATA_MODE=energyplus ./scripts/run_demo.sh
# http://localhost:3000/dashboard
```

**No-data state:** if `results/*` are missing, the API/UI stay in `DATA_MODE=energyplus` and show:

> No EnergyPlus experiment results found. Run the baseline and agent experiment scripts first.

They do **not** silently switch to mock KPIs.

**Explicit mock development mode only:**

```bash
DATA_MODE=mock ./scripts/run_demo.sh
```

| Role | Email | Password |
|------|-------|----------|
| Manager | `manager@twinpilot.demo` | `TwinPilot-Manager-Demo!` |
| Admin | `admin@twinpilot.demo` | `TwinPilot-Admin-Demo!` |
| Operator | `operator@twinpilot.demo` | `TwinPilot-Operator-Demo!` |
| Viewer | `viewer@twinpilot.demo` | `TwinPilot-Viewer-Demo!` |

### C) LLM + stdio MCP experiment (optional)

```bash
./scripts/run_llm_mcp_experiment.sh
# Spawns a separate MCP server over stdio; logs under results/llm_mcp/ and
# manual-verification/mcp-transport/mcp-runtime-trace.jsonl when present.
```

## Baseline methodology

| Fixed across both runs | Differs |
|------------------------|---------|
| `office_5zone.idf` | Controller only |
| `chicago.epw` | Baseline: fixed schedules |
| `OCCUPY-1` occupancy | Agent: hourly SafetyShield-gated `Clg-SetP-Sch` overrides |
| `DemoPeriod` Jul 15–16 | |

Representative measured values after a local run (re-generate; do not trust git history for numbers):

| Metric | Typical baseline | Typical agent |
|--------|------------------|---------------|
| Total energy (kWh) | ~421.51 | ~416.00 |
| HVAC energy (kWh) | ~13.85 | ~13.16 |
| Peak power (kW) | ~19.93 | ~19.64 |
| Occupied comfort violations | 0 | 0 |

Carbon is an **estimate** (kWh × 0.417) — see [docs/carbon.md](docs/carbon.md).

## Safety design

- LLM **cannot** write actuators directly
- MCP tools on the experiment server are non-actuating (observation/context/validation/record only)
- Checks: setpoint min/max, rate limit, heating/cooling deadband, missing/impossible/stale sensors, LLM timeout, MCP failure, malformed JSON, invalid schema, EnergyPlus failure, manual override → **FALLBACK hold**
- Docs: [docs/safety.md](docs/safety.md)

## Troubleshooting

| Symptom | What to do |
|---------|------------|
| Missing EnergyPlus | `./scripts/setup_energyplus.sh` |
| Missing EPW / IDF | Confirm paths in `.env` / `ENERGYPLUS_*` |
| Ollama unavailable | `ollama serve`, then re-run `./scripts/check_prerequisites.sh` |
| Model unavailable | `ollama pull llama3.2:1b` |
| MCP server failing | Check `manual-verification/mcp-transport/mcp-server-stderr.log`; ensure `PYTHONPATH` includes `services/mcp-server` |
| Missing results / dashboard no-data | Run `./scripts/run_baseline.sh` and `./scripts/run_agent.sh` (expected honest empty state beforehand) |
| Ports 8000/3000 occupied | Stop the other process or change ports |
| Want mock UI deliberately | `DATA_MODE=mock ./scripts/run_demo.sh` |

## Environment variables

See [`.env.example`](.env.example). Critical:

- `DATA_MODE=energyplus` (default for measured KPIs) or `DATA_MODE=mock` (**explicit** mock)
- `SIMULATOR_PROVIDER=mock|energyplus`
- `ENERGYPLUS_HOME`, `ENERGYPLUS_MODEL_PATH`, `ENERGYPLUS_WEATHER_PATH`
- `ENERGYPLUS_ALLOW_MOCK_FALLBACK=0` (strict; no silent mock)
- `AGENT_PROVIDER=deterministic|ollama`
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (local prerequisites for LLM path)
- `TWINPILOT_MCP_MODE=energyplus_experiment` (set by the LLM experiment client when spawning the stdio server)

## Tests

```bash
./scripts/check_prerequisites.sh
PYTHONPATH=services/api:services/simulator:services/optimizer:services/mcp-server \
  python -m pytest services/simulator/tests services/optimizer/tests tests/integration -q
```

## Limitations

See [docs/limitations.md](docs/limitations.md). Highlights:

- Controls an **EnergyPlus digital building**, not a physical BMS/BACnet plant
- Live UI ticker may still use the mock twin provider; measured KPIs come from `results/*` when `DATA_MODE=energyplus`
- EnergyPlus install and experiment outputs are local (not committed)
- Ollama + model must be installed locally for the LLM path

## Documentation index

| Doc | Topic |
|-----|--------|
| [docs/architecture.md](docs/architecture.md) | Architecture |
| [docs/setup.md](docs/setup.md) | Setup / troubleshooting |
| [docs/safety.md](docs/safety.md) | Safety |
| [docs/results.md](docs/results.md) | Measured results |
| [docs/demo-script.md](docs/demo-script.md) | Demo script |
| [docs/limitations.md](docs/limitations.md) | Limitations |
| [docs/audit/](docs/audit/) | Repository map, closed-loop trace, dashboard lineage |
| [manual-verification/](manual-verification/) | Independent verification evidence |

## License / status

Prototype / hackathon evaluation software. Not a production BMS controller.
