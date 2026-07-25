# Actuator Code Proof (Phase 6)

Report: `2026-07-25T11:07:18.441284+00:00` · Commit: `589643c3557c56922b79edd886e88ea9e6833474`

## Controlled actuator

- Schedule name: **`Clg-SetP-Sch`**
- File: `services/simulator/twinpilot_simulator/ep_experiment.py`
- Handle acquisition: `api.exchange.get_actuator_handle(... "Schedule:Compact", "Schedule Value", "Clg-SetP-Sch")`
- Write: `api.exchange.set_actuator_value(state_arg, handles["clg"], proposed)` when approved (approx. lines 702–713)

## Loop stages (code)

1. Runtime API state / callbacks — `run_experiment` + pyenergyplus
2. Variable handles — zone temps, occupancy, outdoor
3. Actuator handle — `Clg-SetP-Sch`
4. Observations read each control interval
5. Proposal via `propose_agent_cooling_setpoint` or `proposal_fn`
6. `validate_setpoint_action` (SafetyShield-equivalent)
7. `set_actuator_value` always called (apply or hold)
8. Record `energyplus_actuator_written: True` + applied value
9. Simulation advances; next callback observes new state
10. CSV meters aggregated post-run

## Runtime evidence

See `actuator-runtime-trace.csv` (8 consecutive approved actions with next-state fields).

## Classification

**PROVEN END TO END** for the **deterministic** EnergyPlus agent path (Path A).

LLM Path B also calls the same write path when approved; MCP packaging on Path B is simulated (Phase 9).
