# Code tour — Eco-Loop closed loop (for engineers)

Read this if you need to understand the PoC quickly. Core files are documented with module/function comments.

## One-picture flow

```text
EnergyPlus Runtime API
  → observations
  → (Path C) MCP stdio client/server + Ollama strategy
  → deterministic optimiser / agent proposal
  → SafetyShield validate
  → set_actuator_value(Clg-SetP-Sch)
  → next EnergyPlus state + logs
```

## Entry points (start here)

| Role | File | What to read first |
|------|------|--------------------|
| EnergyPlus experiment | [`services/simulator/twinpilot_simulator/ep_experiment.py`](../services/simulator/twinpilot_simulator/ep_experiment.py) | `run_experiment`, `propose_agent_cooling_setpoint`, `validate_setpoint_action` |
| API SafetyShield | [`services/optimizer/twinpilot_optimizer/safety.py`](../services/optimizer/twinpilot_optimizer/safety.py) | `SafetyShield.validate` |
| MCP server tools | [`services/mcp-server/twinpilot_mcp/energyplus_experiment_server.py`](../services/mcp-server/twinpilot_mcp/energyplus_experiment_server.py) | `build_energyplus_experiment_fastmcp` tool list |
| MCP stdio client | [`services/mcp-server/twinpilot_mcp/stdio_session.py`](../services/mcp-server/twinpilot_mcp/stdio_session.py) | `StdioMcpSession`, `open_energyplus_mcp_session` |
| Path C hybrid | [`scripts/hybrid_supervisory_loop.py`](../scripts/hybrid_supervisory_loop.py) | `call_ollama_strategy`, `setpoint_from_strategy`, `make_hybrid_proposal_fn` |
| Path A scripts | [`scripts/run_baseline.sh`](../scripts/run_baseline.sh), [`scripts/run_agent.sh`](../scripts/run_agent.sh) | shell → `ep_experiment` |
| Dashboard data | API building status + `DATA_MODE=energyplus` | reads `results/*` only |

## How to reproduce

```bash
./scripts/run_baseline.sh && ./scripts/run_agent.sh && ./scripts/compare_results.sh
./scripts/run_hybrid_supervisory_experiment.sh
DATA_MODE=energyplus ./scripts/run_demo.sh
```

## Claims mapping

- **Savings / comfort numbers** → Path A (`results/comparison/`, `final-release/evidence/independent-metrics.json`)
- **LLM + MCP agency** → Path C (`results/hybrid/`, MCP traces)
- **Safety** → `safety-rejection.log` (35°C) + `ollama-fallback.log`
