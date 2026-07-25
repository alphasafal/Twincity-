# Sample office EnergyPlus model

## Files

| File | Description |
|------|-------------|
| `office_5zone.idf` | NREL EnergyPlus example `5ZoneAirCooled.idf` (v24.1), patched for Eco-Loop demos |

## Patches applied

- `RunPeriod` → `DemoPeriod` **July 15–16** (2-day reproducible experiment)
- Extra `Output:Variable` for people/occupancy counts
- `OutputControl:Files` CSV enabled
- Hourly meters: `Electricity:Facility`, `Electricity:HVAC`, `Cooling:Electricity`, `Heating:Electricity`, `Fans:Electricity`
- Optional SQLite output

## Zones

`SPACE1-1` … `SPACE5-1` (+ `PLENUM-1`)

## Thermostat schedules (actuation targets)

- Cooling: `Clg-SetP-Sch` (Runtime actuator `Schedule:Compact` / `Schedule Value`)
- Heating: `Htg-SetP-Sch`
- Occupancy: `OCCUPY-1`

## Usage

```bash
export ENERGYPLUS_MODEL_PATH=$PWD/building-models/sample-office/office_5zone.idf
export ENERGYPLUS_WEATHER_PATH=$PWD/building-models/weather/chicago.epw
./scripts/run_baseline.sh
./scripts/run_agent.sh
```
