# Runtime-modified building model

## Baseline (static IDF)

- File: `building-models/sample-office/office_5zone.idf`
- Weather: `building-models/weather/chicago.epw`
- Packaged in the submission ZIP as `building-models/base-office.idf`

## How the model is modified at runtime

Eco-Loop does **not** rewrite the `.idf` on disk between timesteps. During closed-loop evaluation the EnergyPlus **Runtime API** writes the cooling setpoint schedule actuator:

`set_actuator_value(... "Clg-SetP-Sch" ...)`

That is the live model edit required by the problem statement (forward injection of control actions into the running simulation).

## Artifacts proving the modified schedule

| File | Contents |
|------|----------|
| `post-control-cooling-schedule.csv` | Per-timestep baseline vs Runtime-written setpoint + next-zone temperature |
| `runtime-modified-clg-setp-sch.json` | Full actuator write timeline (48 approved writes) |
| `../final-actuator-trace.csv` | Authoritative closed-loop trace with `clg_setp_sch_actuator_write=True` |

## Fairness

Baseline and agent use the **same** IDF, EPW, occupancy, and run period. Only the controller (schedule actuator writes) differs. See `../experiment-fairness.md`.
