# Comfort Verification (Phase 8)

Report: `2026-07-25T11:07:18.441284+00:00`

## Policy (from `SafetyLimits` / ep_experiment)

- Occupied comfort band: **21.0–26.0 °C**
- Occupancy-dependent: yes (occupied when occupant count > 0)
- Timestep: hourly meter rows in `eplusout.csv`
- Zones: SPACE1-1 … SPACE5-1

## Independent recompute

From raw CSV (see `independent-comfort-analysis.csv` — empty event list ⇒ zero violations):

| Run | Violation hours | Degree-hours |
|-----|-----------------|--------------|
| Baseline | 0.0 | 0.0 |
| Agent | 0.0 | 0.0 |

Matches application `occupied_comfort_*` fields.

**VERIFIED** claim of 0 / 0 for deterministic baseline and agent.

Note: LLM Path B in clean-room produced non-zero comfort hours (9.0) — separate controller; do not mix with Path A claims.
