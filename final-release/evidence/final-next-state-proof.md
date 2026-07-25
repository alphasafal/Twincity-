# Final Next-State Proof

Generated: 2026-07-25T11:44:51.624870+00:00

## Claim

EnergyPlus Runtime API writes `Clg-SetP-Sch` via `set_actuator_value`, and the following timestep returns a new zone temperature observation.

## Code path

- Handle: `get_actuator_handle(..., "Schedule:Compact", "Schedule Value", "Clg-SetP-Sch")` in `ep_experiment.py`
- Write: `api.exchange.set_actuator_value(state, handles["clg"], value)`
- Evidence flags per action: `energyplus_actuator_written`, `energyplus_action_accepted`

## Five+ consecutive closed-loop rows

| sim_time | occ | zone_T | outdoor | current_SP | proposed | shield | executed | write | next_time | next_zone_T |
|---|---:|---:|---:|---:|---:|---|---:|---|---|---:|
| 07-15T00:15 | 0.0 | 22.054832739026942 | 24.200000000000003 | 23.9 | 24.9 | approved | 24.9 | True | 07-15T01:15 | 21.709545981078833 |
| 07-15T01:15 | 0.0 | 21.709545981078833 | 20.0 | 24.9 | 25.9 | approved | 25.9 | True | 07-15T02:15 | 21.480160241773824 |
| 07-15T02:15 | 0.0 | 21.480160241773824 | 19.85 | 25.9 | 26.9 | approved | 26.9 | True | 07-15T03:15 | 21.260098069107162 |
| 07-15T03:15 | 0.0 | 21.260098069107162 | 19.275 | 26.9 | 27.9 | approved | 27.9 | True | 07-15T04:15 | 21.074592734486323 |
| 07-15T04:15 | 0.0 | 21.074592734486323 | 18.9 | 27.9 | 28.0 | approved | 28.0 | True | 07-15T05:23 | 21.288305768027545 |
| 07-15T05:23 | 0.0 | 21.288305768027545 | 19.325 | 28.0 | 28.0 | approved | 28.0 | True | 07-15T06:19 | 22.259281419623754 |
| 07-15T06:19 | 0.0 | 22.259281419623754 | 21.0 | 28.0 | 27.0 | approved | 27.0 | True | 07-15T07:15 | 22.3449646301428 |
| 07-15T07:15 | 0.0 | 22.3449646301428 | 22.75 | 27.0 | 26.0 | approved | 26.0 | True | 07-15T08:20 | 23.181358033947816 |

## Verification

- Consecutive rows with actuator write True: 8
- Consecutive rows with following zone temperature: 8
- Full trace: `final-release/evidence/final-actuator-trace.csv` (48 rows)
- Verdict: **PASS**
