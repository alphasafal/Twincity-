# TwinPilot — Eco-Loop Building Agents

**Verifiable autonomous building optimization** with a real EnergyPlus closed-loop experiment path and an independent Safety Shield.

> AI proposes → safety validates → EnergyPlus (or mock twin) executes → results are auditable.

---

## Problem statement

Buildings waste energy when HVAC setpoints ignore occupancy, weather, and comfort constraints. Fully autonomous LLM control is unsafe. Operators need a closed loop that is **measurable**, **reproducible**, and **hard-gated** by deterministic safety rules.

## Proposed solution

TwinPilot / Eco-Loop separates **proposal** from **actuation**:

1. Observe building state (EnergyPlus Runtime API or mock twin)
2. Agent proposes a cooling-setpoint adjustment
3. Deterministic Safety Shield validates range, rate, deadband, sensors, and infrastructure health
4. Only approved actions are injected (EnergyPlus schedule actuator or mock apply)
5. Baseline vs agent experiments quantify energy, peak, comfort, and carbon *estimates*

## Architecture

```text
Web / Mobile / MCP ──► FastAPI RuntimeHub ──► Mock twin (default UI demo)
                         │
                         ├── Optimizer + SafetyShield
                         └── Agent (deterministic | Ollama)

EnergyPlus evidence path (evaluation):
  scripts/run_baseline.sh | run_agent.sh
    → ep_experiment (pyenergyplus Runtime API)
    → results/{baseline,agent,comparison}/
```

Details: [docs/architecture.md](docs/architecture.md) · Audit map: [docs/audit/repository-map.md](docs/audit/repository-map.md)

## Technologies

| Layer | Stack |
|-------|--------|
| API | FastAPI, SQLAlchemy, JWT |
| Optimizer / Safety | `twinpilot-optimizer` |
| Simulator | Mock twin · EnergyPlus 24.1 Runtime API |
| Agent | Deterministic (default) · Ollama (optional) |
| Web | Next.js 15, React 19, Tailwind |
| Mobile | Expo 52 |
| MCP | `twinpilot-mcp` |
| Experiments | `scripts/run_*.sh` → JSON under `results/` |

## Installation

```bash
./scripts/setup.sh                 # Python venv, packages, pnpm, .env
./scripts/setup_energyplus.sh      # EnergyPlus 24.1 → third_party/EnergyPlus
```

Or: `make setup`. Copy `.env.example` → `.env` (done by setup).

**Versions:** Python ≥3.11, Node 20+/22 (see `.nvmrc`), pnpm 10, EnergyPlus 24.1.0.

## Demo procedure

### A) Measured EnergyPlus closed loop (quote these numbers)

```bash
./scripts/run_baseline.sh
./scripts/run_agent.sh
./scripts/compare_results.sh
# → results/comparison/comparison.json
```

### B) Operator UI (mock twin — clearly labeled)

```bash
./scripts/run_demo.sh
# http://localhost:3000
```

| Role | Email | Password |
|------|-------|----------|
| Manager | `manager@twinpilot.demo` | `TwinPilot-Manager-Demo!` |
| Admin | `admin@twinpilot.demo` | `TwinPilot-Admin-Demo!` |
| Operator | `operator@twinpilot.demo` | `TwinPilot-Operator-Demo!` |
| Viewer | `viewer@twinpilot.demo` | `TwinPilot-Viewer-Demo!` |

Full walkthrough: [docs/demo-script.md](docs/demo-script.md)

## Baseline methodology

| Fixed across both runs | Differs |
|------------------------|---------|
| `office_5zone.idf` | Controller only |
| `chicago.epw` | Baseline: fixed schedules |
| `OCCUPY-1` occupancy | Agent: hourly SafetyShield-gated `Clg-SetP-Sch` overrides |
| `DemoPeriod` Jul 15–16 | |

## Actual measured results

Default hackathon dashboard uses `DATA_MODE=energyplus` and reads `results/*` (no ×1.12).

From `results/comparison/comparison.json` (comfort-zero tuned controller):

| Metric | Baseline | Agent | Reduction |
|--------|----------|-------|-----------|
| Total energy (kWh) | 421.51 | 416.00 | **1.31%** |
| HVAC energy (kWh) | 13.85 | 13.16 | **4.98%** |
| Peak power (kW) | 19.93 | 19.64 | **1.47%** |
| Occupied comfort violation hours | 0 | **0** | — |
| Comfort degree-hours | 0 | **0** | — |
| Actions (approved / rejected / fallback) | — | **48 / 0 / 0** | — |

Carbon is an **estimate** (kWh × 0.417) — see [docs/carbon.md](docs/carbon.md).  
Full methodology and multi-scenario / LLM-MCP results: [docs/results.md](docs/results.md).

## Safety design

- LLM **cannot** write actuators directly
- Checks: setpoint min/max, rate limit, heating/cooling deadband, missing/impossible/stale sensors, LLM timeout, MCP failure, malformed JSON, invalid schema, EnergyPlus failure, manual override → **FALLBACK hold**
- Docs: [docs/safety.md](docs/safety.md)

## Repository structure

```
apps/web, apps/mobile
services/{api,optimizer,simulator,agent,mcp-server}
building-models/sample-office/office_5zone.idf
building-models/weather/chicago.epw
scripts/{setup,setup_energyplus,run_demo,run_baseline,run_agent,compare_results}.sh
results/{baseline,agent,comparison}/
docs/ + docs/audit/
FINAL_HACKATHON_READINESS_REPORT.md
```

## Limitations

See [docs/limitations.md](docs/limitations.md). Highlights:

- UI defaults to **mock** twin; EnergyPlus proof is the experiment harness
- No production BMS/BACnet connectors
- EnergyPlus install is downloaded locally (not committed)

## Future scope

- Live dashboard fed from EnergyPlus co-simulation ticks
- Per-zone EMS actuators
- Full ASHRAE comfort outputs
- Production BMS adapters under the same Safety Shield

## Environment variables

See [`.env.example`](.env.example). Critical:

- `SIMULATOR_PROVIDER=mock|energyplus`
- `ENERGYPLUS_HOME`, `ENERGYPLUS_MODEL_PATH`, `ENERGYPLUS_WEATHER_PATH`
- `ENERGYPLUS_ALLOW_MOCK_FALLBACK=0` (strict; no silent mock)
- `AGENT_PROVIDER=deterministic|ollama`

## Tests

```bash
make test
PYTHONPATH=services/simulator:services/optimizer python -m pytest services/simulator/tests services/optimizer/tests -q
```

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
| [FINAL_HACKATHON_READINESS_REPORT.md](FINAL_HACKATHON_READINESS_REPORT.md) | Scorecard |

## License / status

Internal demo / research prototype. **Not for controlling live buildings without qualified engineering review.**
