# Architecture — TwinPilot / Eco-Loop Building Agents

## Two loops

### A) Interactive mock closed loop (default demo)

```text
Web/Mobile/MCP → FastAPI RuntimeHub → MockBuildingSimulator
                 → Optimizer / SafetyShield → apply → DB/WS dashboard
```

`SIMULATOR_PROVIDER=mock` (default). Suitable for UI, MCP, and operator workflow demos.

### B) Measured EnergyPlus closed loop (evaluation evidence)

```text
scripts/run_baseline.sh | run_agent.sh
  → twinpilot_simulator.ep_experiment
  → EnergyPlus 24.x Runtime API (pyenergyplus)
  → observations → agent proposal → safety gate → Clg-SetP-Sch actuator
  → results/*/summary.json → compare_results.sh
```

Identical IDF, EPW, occupancy schedule, and run period. **Only the controller differs.**

## Safety boundary

The LLM (optional Ollama) **never** writes actuators directly.

```text
Agent proposal → SafetyShield / validate_setpoint_action → approved action only → EnergyPlus / mock apply
```

## Packages

| Path | Role |
|------|------|
| `services/api` | FastAPI, auth, RuntimeHub |
| `services/optimizer` | Multi-objective planner + SafetyShield |
| `services/simulator` | Mock twin + EnergyPlus adapter + `ep_experiment` |
| `services/agent` | Deterministic / Ollama providers |
| `services/mcp-server` | MCP tools (no unrestricted actuation) |
| `apps/web` | Next.js operator UI |
| `apps/mobile` | Expo approvals |
| `building-models` | IDF + EPW |
| `scripts/` | Setup, demo, EnergyPlus experiments |

See also `docs/ARCHITECTURE.md` (legacy diagrams) and `docs/audit/repository-map.md`.
