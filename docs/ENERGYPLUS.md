# EnergyPlus integration

Default UI demo uses **`SIMULATOR_PROVIDER=mock`**.  
Measured closed-loop evidence uses the **experiment scripts** (recommended for evaluators).

## Assets

| Path | Role |
|------|------|
| `building-models/sample-office/office_5zone.idf` | 5-zone VAV office (DemoPeriod Jul 15–16) |
| `building-models/weather/chicago.epw` | TMY3 weather |
| `third_party/EnergyPlus/` | Local install via `./scripts/setup_energyplus.sh` (not committed) |

## Environment

| Variable | Purpose |
|----------|---------|
| `SIMULATOR_PROVIDER=energyplus` | Select adapter in API |
| `ENERGYPLUS_HOME` | Install root containing `energyplus` + `pyenergyplus` |
| `ENERGYPLUS_MODEL_PATH` | IDF |
| `ENERGYPLUS_WEATHER_PATH` | EPW |
| `ENERGYPLUS_ALLOW_MOCK_FALLBACK=1` | **Explicit** debug opt-in to mock; default is **strict fail** |

## Measured closed loop (preferred)

```bash
./scripts/setup_energyplus.sh
./scripts/run_baseline.sh
./scripts/run_agent.sh
./scripts/compare_results.sh
```

Implementation: `services/simulator/twinpilot_simulator/ep_experiment.py`  
Actuator: `Schedule:Compact` / `Schedule Value` / `Clg-SetP-Sch`

## Adapter behaviour

- **Strict (default):** missing EnergyPlus → `EnergyPlusUnavailableError` (no silent mock).
- **Fallback:** only if `ENERGYPLUS_ALLOW_MOCK_FALLBACK=1`.
- Health endpoint reports `provider`, `strict`, `last_experiment_total_energy_kwh`.

```bash
make energyplus-check
```
