# Results — Baseline vs Agent (EnergyPlus)

## Methodology

| Item | Value |
|------|-------|
| Building model | `building-models/sample-office/office_5zone.idf` |
| Weather | `building-models/weather/chicago.epw` |
| Occupancy schedule | `OCCUPY-1` (identical) |
| Period | `DemoPeriod` Jul 15–16 |
| Baseline controller | Fixed IDF thermostat schedules (no overrides) |
| Agent controller | Hourly cooling-setpoint overrides via Runtime actuator, SafetyShield-gated |
| Carbon | Estimate = total kWh × **0.417 kg/kWh** (documented factor) |

## How to reproduce

```bash
./scripts/run_baseline.sh
./scripts/run_agent.sh
./scripts/compare_results.sh
```

## Measured results (this audit environment)

From `results/comparison/comparison.json`:

| Metric | Baseline | Agent | Δ | % |
|--------|----------|-------|---|---|
| Total energy (kWh) | 421.5057 | 406.2102 | −15.2955 | **−3.63%** |
| HVAC energy (kWh) | 13.8459 | 12.1566 | −1.6893 | **−12.20%** |
| Peak power (kW) | 19.9325 | 19.4989 | −0.4336 | **−2.18%** |
| Carbon estimate (kg) | 175.7679 | 169.3897 | −6.3782 | −3.63% |
| Occupied comfort violation hours | 0.0 | 1.0 | +1.0 | — |

Agent actions: **48** approved, **0** rejected, **0** fallback.

## Interpretation

- Energy and HVAC reductions are **measured EnergyPlus meter deltas**, not invented marketing numbers.
- A small comfort tradeoff (+1 occupied violation hour under the documented band) is reported honestly.
- Dashboard mock KPI “savings %” is **not** this table — see `docs/audit/dashboard-data-lineage.md`.
