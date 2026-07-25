# Dashboard Real-Data Proof

Generated: 2026-07-25T11:52:34.972138+00:00

## Configuration
- DATA_MODE=energyplus (hackathon default)
- API `/buildings/{id}/status` and `/experiments/comparison`

## Observed
- data_mode: `energyplus`
- data_label: `energyplus_experiment_results`
- data_source_visible: `EnergyPlus experiment results (results/*)`
- simulated: `False`
- synthetic_multiplier_applied: `False`
- energy_saved_today_pct (display): `1.31`
- peak_demand_reduction_pct: `1.47`
- carbon_avoided_today_kg (**estimate** delta): `2.3`
- comfort_compliance_pct: `100.0`

## Match vs fresh files
| Metric | Independent % | API reductions | Match |
|---|---:|---:|---|
| Total energy | 1.306222 | 1.3062 | True |
| HVAC energy | 4.97548 | 4.9755 | True |
| Peak power | 1.467453 | 1.4675 | True |

- Baseline total kWh file/API: 421.5057 / 421.51
- Agent total kWh file/API: 415.9999 / 416.0
- No ×1.12 multiplier: True
- Pages HTTP 200: /dashboard, /live-demo

## Verdict
**PASS**
