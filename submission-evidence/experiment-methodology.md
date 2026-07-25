# Experiment methodology

## Identical inputs (within each scenario)

- IDF building model (scenario-patched RunPeriod / occupancy as documented)
- EPW weather file: `building-models/weather/chicago.epw`
- Occupancy schedule family: `OCCUPY-1`
- Simulation period: scenario-specific DemoPeriod
- Initial conditions: EnergyPlus warm-up as provided by the IDF

## Controllers

- **Baseline:** fixed thermostat schedules (no Runtime overrides)
- **Agent:** hourly cooling-setpoint proposals → SafetyShield gate → `Clg-SetP-Sch` actuator

## Metrics

- Total / HVAC energy from EnergyPlus CSV meters (J → kWh)
- Peak power from hourly facility meter
- Carbon **estimate** = kWh × 0.417 kg/kWh (see `docs/carbon.md`)
- Comfort: occupied-hour band [21, 26] °C; degree-hours = sum of deviations

## Dashboard

- `DATA_MODE=energyplus` (hackathon default) serves `results/*` — no ×1.12 synthetic savings

## Reproduction

```bash
./scripts/run_baseline.sh && ./scripts/run_agent.sh && ./scripts/compare_results.sh
./scripts/run_scenarios.sh
./scripts/run_llm_mcp_experiment.sh
python scripts/build_submission_evidence.py
```

See multi-scenario-comparison.json for normal_summer / high_occupancy / hot_peak.
