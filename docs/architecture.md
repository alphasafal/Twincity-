# Architecture — TwinPilot / Eco-Loop Building Agents

This prototype controls an **EnergyPlus digital building**, not a physical BMS.

**HirePro mapping:** EnergyPlus = sandbox · open-source LLM (Ollama) = brain · MCP stdio = tool bus · SafetyShield = hard gate · `Clg-SetP-Sch` = forward injection.

## Closed-loop diagram

```text
EnergyPlus Runtime API (observations)
        │
        ▼
MCP client ──stdio──► separate MCP server process (tools/list, tools/call)
        │
        ▼
Ollama (llama3.2:1b)  →  supervisory ECM / strategy JSON
        │
        ▼
Deterministic optimiser  →  numeric cooling setpoint
        │
        ▼
SafetyShield validate  →  approve | reject | fallback
        │
        ▼
EnergyPlus actuator write  →  Schedule:Compact Clg-SetP-Sch
        │
        ▼
Next EnergyPlus state  →  expected vs actual  →  self-correction
```

Line: **AI proposes. SafetyShield validates. EnergyPlus executes.**

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

### Path C — Hybrid supervisory loop (agentic / MCP scoring)

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

## Tool-calling architecture (MCP)

Transport: **stdio JSON-RPC** between an MCP client (experiment loop) and a **separate** MCP server process (`twinpilot_mcp`).

Authoritative proof: `final-release/evidence/mcp-process-proof.md`, `final-release/evidence/mcp-runtime-trace.jsonl`, hybrid `summary.json` (`mcp_pids_differ: true`).

### Experiment tool catalog (Path B/C server)

| Tool | Role |
|------|------|
| `get_building_observation` | Normalize EnergyPlus Runtime observation payload |
| `propose_or_prepare_control_context` | Build structured context + advisor prompt hint |
| `select_energy_conservation_measure` | Record/validate supervisory ECM strategy (no actuation) |
| `validate_control_action` | Advisory SafetyShield-equivalent check |
| `get_controller_constraints` | Cooling setpoint limits |
| `record_control_decision` | Audit log of decisions |
| `get_recent_energy_history` | Client-supplied history echo |
| `get_previous_action_outcome` | Expected-vs-actual for self-correction |

Implementation: `services/mcp-server/twinpilot_mcp/energyplus_experiment_server.py`  
Client: `services/mcp-server/twinpilot_mcp/stdio_session.py` (`list_tools`, `call_tool`; does **not** import `handlers.call_tool`).

### Protocol events judges should see

From `final-release/evidence/mcp-runtime-trace.jsonl` / hybrid MCP trace:

1. `initialize` — session handshake  
2. `tools/list` — catalog discovery  
3. `tools/call` — e.g. `get_building_observation`, `select_energy_conservation_measure`, `validate_control_action`

## Prompt engineering strategy

**Path C supervisory prompt** (`scripts/hybrid_supervisory_loop.py` → `call_ollama_strategy`):

- Model: local Ollama `llama3.2:1b` (`format: json`)
- Instruction: HVAC supervisory agent; reply **only** with JSON
- Schema fields: `strategy`, `target_cooling_range_c`, `control_horizon_minutes`, `confidence`, `reason`, `expected_hvac_effect_pct`
- Allowed strategies: `COMFORT_FIRST`, `ECO_MODE`, `UNOCCUPIED_SETBACK`, `PRE_COOL`, `PEAK_DEMAND_LIMIT`, `RECOVERY`, `HOLD_CURRENT_POLICY`
- Guardrails in prompt: do not invent actuators; prefer comfort-safe strategies when occupied
- On parse/HTTP failure → deterministic `HOLD_CURRENT_POLICY` fallback (still SafetyShield-gated)

**Path B setpoint prompt hint** (MCP tool `propose_or_prepare_control_context`):

```text
Reply ONLY with JSON:
{"proposed_cooling_setpoint_c": number, "reason": string, "confidence": number}.
Stay within 22-28C. Do not execute actuators.
```

**Authority split:** LLM never calls EnergyPlus actuators. Numeric setpoints come from the deterministic optimiser (Path C) or validated proposal (Path B). SafetyShield is the only gate before `Clg-SetP-Sch`.

## Latency management

| Concern | Approach |
|---------|----------|
| LLM latency | One Ollama call per control hour; 12s HTTP timeout |
| Fast numerics | Deterministic optimiser maps strategy → setpoint in-process (microseconds) |
| Safety | Local SafetyShield before every write (no network) |
| MCP | Local stdio; separate process; no cloud round-trip |
| Failure | Ollama down → deterministic fallback; unsafe 35°C → reject, no actuator write |

**Measured Path C stage timing** (obs → next strategy/decision hop, `final-release/evidence/hybrid/stage_log.jsonl`):

| Stat | Seconds |
|------|---------|
| p50 | ~5.6 |
| p95 | ~6.5 |
| max | ~6.6 |

Per-hour LLM cost dominates; the numerical/safety path is not the bottleneck.

## Handling lengthy simulation logs

EnergyPlus and agent loops emit large traces. Strategy:

| Artifact | Purpose | Submission handling |
|----------|---------|---------------------|
| `results/*/summary.json` | Compact KPIs | Included (or mirrored under `final-release/evidence/`) |
| `results/agent/actions.json` | Full decision list | Summarized to CSV in ZIP (`action-log.csv`) |
| `*/stage_log.jsonl` | Per-stage timeline | Truncated excerpts in ZIP; full under `results/` / `final-release/evidence/` |
| `*/mcp-runtime-trace.jsonl` | MCP protocol proof | Included; large but searchable for `initialize` / `tools/call` |
| `self_correction.jsonl` | Expected vs actual | Included (hybrid) |
| EnergyPlus eplusout.* | Native sim dumps | **Not** shipped; regenerated by scripts |

ZIP builder keeps judge-facing excerpts; regenerating experiments rewrites `results/**` (gitignored).

## Safety boundary

The LLM (optional local Ollama) **never** writes actuators directly.

```text
Agent proposal → SafetyShield / validate_setpoint_action → approved action only → EnergyPlus / mock apply
```

Evidence: `final-release/evidence/safety-rejection.log` (35°C rejected), `final-release/evidence/ollama-fallback.log`.

## Packages

| Path | Role |
|------|------|
| `services/api` | FastAPI, auth, RuntimeHub |
| `services/optimizer` | Multi-objective planner + SafetyShield |
| `services/simulator` | Mock twin + EnergyPlus adapter + `ep_experiment` |
| `services/agent` | Deterministic / Ollama providers |
| `services/mcp-server` | MCP server (stdio; EnergyPlus experiment tools + API-backed tools) |
| `apps/web` | Next.js operator UI / savings dashboard |
| `apps/mobile` | Expo approvals |
| `building-models` | Baseline IDF + EPW |
| `final-release/evidence/building-models` | Runtime-modified schedule artifacts |
| `scripts/` | Setup, demo, EnergyPlus experiments, prerequisite checks |

See also `docs/audit/repository-map.md` and `manual-verification/`.
