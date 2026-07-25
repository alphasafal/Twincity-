# Building models

Assets for the **optional** EnergyPlus path (`SIMULATOR_PROVIDER=energyplus`).

The TwinPilot demo runs on the **mock simulator** by default and does not require files here.

## Layout

```
building-models/
  sample-office/   # Place a sample commercial office IDF here
  weather/         # Place EPW weather files here
```

## Usage

```bash
export SIMULATOR_PROVIDER=energyplus
export ENERGYPLUS_HOME=/path/to/EnergyPlus
export ENERGYPLUS_MODEL_PATH=$PWD/building-models/sample-office/your-model.idf
export ENERGYPLUS_WEATHER_PATH=$PWD/building-models/weather/your-weather.epw
make energyplus-check
```

See [docs/ENERGYPLUS.md](../docs/ENERGYPLUS.md).

**Note:** Full DOE / OpenStudio models are not vendored in this repository (license/size). Add your own IDF/EPW locally.
