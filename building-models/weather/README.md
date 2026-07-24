# Weather (EPW)

Place EnergyPlus weather files (`.epw`) here, for example a Bengaluru or similar climate file matching the demo office location.

```bash
export ENERGYPLUS_WEATHER_PATH=/absolute/path/to/building-models/weather/your-climate.epw
```

EPW files are not vendored in-repo. Without them, the EnergyPlus adapter falls back to the mock twin.
