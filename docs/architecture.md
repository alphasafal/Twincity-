# Architecture — TwinPilot / Eco-Loop Building Agents

This prototype controls an **EnergyPlus digital building**, not a physical BMS.

## Three measured paths (honest layering)

### Path A — Authoritative savings (deterministic optimiser)

```text
scripts/run_baseline.sh | run_agent.sh
  → twinpilot_simulator.ep_experiment
  → EnergyPlus 24.x Runtime API (pyenergyplus)
  → observations → deterministic optimiser → SafetyShield → Clg-SetP-Sch
  → results/*/summary.json → compare_results.sh
```

Identical IDF, EPW, occupancy schedule, and run period. **Only the controller differs.**

**Authoritative comfort-zero claim:** HVAC **4.98%**, total **1.31%**, peak **1.47%**, comfort **0 h**.

### Path B — LLM setpoint proposal via separate MCP stdio

```text
EnergyPlus observation
  → MCP client → stdio → separate MCP server
  → Ollama structured setpoint proposal
  → SafetyShield → Clg-SetP-Sch → next state
```

Proves process isolation, tools/call, Ollama JSON, and fallback. Does **not** replace Path A as the primary savings claim.

### Path C — Hybrid supervisory loop (winning defence)

```text
EnergyPlus observations
  → MCP client → stdio → separate MCP server
  → Ollama selects energy-conservation strategy (ECM)
  → deterministic optimiser computes numeric setpoints
  → SafetyShield validates
  → Clg-SetP-Sch actuator
  → next EnergyPlus state
  → expected vs actual outcome → strategy correction
```

Run: `./scripts/run_hybrid_supervisory_experiment.sh` → `results/hybrid/`.

The LLM provides supervisory intelligence and tool-based strategy selection. Deterministic optimisation handles fast numerical control. SafetyShield retains final authority.

Do **not** describe in-process handler calls as remote MCP. Paths B/C use a **separate OS process** over stdio.

### Interactive mock (explicit `DATA_MODE=mock` only)

```text
Web/Mobile → FastAPI RuntimeHub → MockBuildingSimulator
             → Optimizer / SafetyShield → apply → DB/WS dashboard
```

`results/*` artifacts are **generated locally and not committed**. When `DATA_MODE=energyplus` and results are missing, the dashboard shows an honest no-data state.

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
