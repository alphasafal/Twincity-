# EnergyPlus (optional)

TwinPilot’s default twin is the **mock simulator** (`SIMULATOR_PROVIDER=mock`). An **EnergyPlus adapter** exists at `services/simulator/twinpilot_simulator/energyplus.py` for environments that have EnergyPlus Python bindings installed.

EnergyPlus is **optional**. The demo does not require it.

---

## Environment variables

| Variable | Purpose |
|----------|---------|
| `SIMULATOR_PROVIDER` | Set to `energyplus` to select the adapter |
| `ENERGYPLUS_HOME` | Directory containing EnergyPlus / `pyenergyplus` |
| `ENERGYPLUS_MODEL_PATH` | Path to an `.idf` (or compatible) model |
| `ENERGYPLUS_WEATHER_PATH` | Path to an `.epw` weather file |

Placeholders and notes:

- `building-models/sample-office/` — sample IDF location (not shipped as a full DOE model)
- `building-models/weather/` — EPW weather files

---

## Behavior

1. If any of home/model/weather are missing → adapter marks itself unavailable and uses **MockBuildingSimulator** fallback.
2. If `pyenergyplus.api` cannot be imported → same fallback with an error string in health.
3. When “available”, the current adapter still mirrors state through the mock schema for product continuity; full co-simulation wiring is **environment-specific** and not claimed as complete in this demo.

Check readiness:

```bash
make energyplus-check
# or
bash infrastructure/scripts/energyplus-check.sh
```

Compose profile `energyplus` starts `api` + `web` with EnergyPlus env vars / `building-models` mount. You must supply a real EnergyPlus install on the host or image; the stock demo image does not bundle EnergyPlus.

---

## Honest limitations

- Not a certified EnergyPlus co-simulation product.
- Savings shown in the UI remain **simulated** unless you replace the twin with a validated site model.
- No Honeywell/BMS bridge is implied by enabling EnergyPlus.
