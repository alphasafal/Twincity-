# Architecture — TwinPilot / Eco-Loop Building Agents

This prototype controls an **EnergyPlus digital building**, not a physical BMS.

## Two loops

### A) Interactive mock closed loop (explicit `DATA_MODE=mock` only)

```text
Web/Mobile → FastAPI RuntimeHub → MockBuildingSimulator
             → Optimizer / SafetyShield → apply → DB/WS dashboard
```

Mock mode must be selected explicitly (`DATA_MODE=mock`). It does not invent EnergyPlus savings.

### B) Measured EnergyPlus closed loop (evaluation evidence)

```text
scripts/run_baseline.sh | run_agent.sh
  → twinpilot_simulator.ep_experiment
  → EnergyPlus 24.x Runtime API (pyenergyplus)
  → observations → agent proposal → safety gate → Clg-SetP-Sch actuator
  → results/*/summary.json → compare_results.sh
```

Identical IDF, EPW, occupancy schedule, and run period. **Only the controller differs.**

`results/*` artifacts are **generated locally and not committed**.

When `DATA_MODE=energyplus` and results are missing, the dashboard shows an honest no-data state (it does not fall back to mock KPIs).

### C) Optional LLM + separate local MCP server (stdio)

```text
EnergyPlus observation
  → MCP client (experiment process)
  → stdio transport
  → separate MCP server process (`python -m twinpilot_mcp`, TWINPILOT_MCP_MODE=energyplus_experiment)
  → MCP tools (get_building_observation, propose_or_prepare_control_context,
               validate_control_action, get_controller_constraints, record_control_decision)
  → Ollama structured proposal (local prerequisite)
  → SafetyShield (authoritative actuation gate in ep_experiment)
  → EnergyPlus actuator
  → next simulation state
```

Do **not** describe in-process handler calls as remote MCP. The authoritative experiment path uses a **separate OS process** over stdio.

## Safety boundary

The LLM (optional local Ollama) **never** writes actuators directly.

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
| `services/mcp-server` | MCP server (stdio; EnergyPlus experiment tools + API-backed tools) |
| `apps/web` | Next.js operator UI |
| `apps/mobile` | Expo approvals |
| `building-models` | IDF + EPW |
| `scripts/` | Setup, demo, EnergyPlus experiments, prerequisite checks |

See also `docs/audit/repository-map.md` and `manual-verification/`.
