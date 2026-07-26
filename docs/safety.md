# Safety Design

## Principle

**The LLM never bypasses the Safety Shield.** Proposals are advisory until a deterministic validator approves them. On failure, the system holds the last safe setpoint (fallback) — it does not invent an uncontrolled action.

## Deterministic controls

| Control | Implementation |
|---------|----------------|
| Min/max cooling setpoint | `ConstraintLimits` / `SafetyLimits` |
| Min/max heating setpoint | same |
| Max setpoint change / interval | `max_setpoint_change_per_interval` |
| Heating/cooling deadband | `heating_cooling_deadband_c` |
| Missing temperature / occupancy | `missing_temperature`, `missing_occupancy` |
| Impossible sensor values | range + NaN/Inf checks |
| Stale sensors | `data_age_seconds` vs `maximum_data_age_seconds` |
| LLM timeout | `llm_timeout` → FALLBACK |
| MCP failure | `mcp_failure` → FALLBACK |
| Malformed response | `malformed_agent_response` |
| Invalid action schema | `invalid_action_schema` |
| EnergyPlus failure | `energyplus_failure` / experiment non-zero exit |
| Manual override | `manual_override` blocks auto actuation |
| Emergency fallback | hold last safe cooling schedule value in E+ loop |

## EnergyPlus injection path

```text
propose_agent_cooling_setpoint → validate_setpoint_action
  → approved? set_actuator_value(Clg-SetP-Sch)
  → else set_actuator_value(last_safe)
```

Logged in `results/agent/actions.json` with `disposition`: `approved` | `rejected` | `fallback`.

## Tests

```bash
cd services/api && .venv/bin/pytest ../../services/optimizer/tests/test_safety_failure_modes.py -q
PYTHONPATH=services/simulator:services/optimizer .venv/bin/pytest services/simulator/tests -q
PYTHONPATH=services/api:services/optimizer:services/simulator:services/agent \
  .venv/bin/pytest tests/integration/test_failure_modes.py -q
```
