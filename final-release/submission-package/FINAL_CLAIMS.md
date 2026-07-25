# Final Claims — Eco-Loop Building Agents

## Primary claim (Path A — authoritative)

Under identical EnergyPlus building, weather, occupancy and simulation conditions, Eco-Loop reduced simulated HVAC energy by **4.98%**, total energy by **1.31%** and peak demand by **1.47%**, while maintaining **zero** occupied comfort-violation hours and **zero** comfort degree-hours.

| Metric | Baseline | Eco-Loop | Improvement |
|--------|----------|----------|-------------|
| Total energy | 421.51 kWh | 416.00 kWh | 1.31% |
| HVAC energy | 13.85 kWh | 13.16 kWh | 4.98% |
| Peak power | 19.93 kW | 19.64 kW | 1.47% |
| Comfort violations | 0 h | 0 h | — |
| Comfort degree-hours | 0 | 0 | — |

## Multi-scenario Path A

| Scenario | Total | HVAC | Peak | Comfort |
|----------|-------|------|------|---------|
| Normal summer | 1.31% | 4.98% | 1.47% | 0 h |
| Hot / peak day | 1.27% | 5.07% | 1.08% | 0 h |
| High occupancy | 1.34% | 5.18% | 1.45% | 0 h |

## Path C hybrid supervisory

LLM selects strategy via MCP → deterministic optimiser → SafetyShield → actuator → self-correction.
48 approved / 0 rejected / 0 fallback; comfort 0 h; proves LLM material involvement.
Path A remains the authoritative savings claim.

## Non-claims
- Not a physical BMS deployment.
- Not claiming Path A 4.98% was produced solely by the LLM writing every setpoint.
