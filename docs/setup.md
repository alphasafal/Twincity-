# Setup

## Requirements

- Python **3.11+**
- Node.js **20+** and **pnpm**
- Linux x86_64 recommended for EnergyPlus 24.1 binaries
- Optional: Docker, Ollama

## Quick start (mock demo)

```bash
./scripts/setup.sh
# or: make setup
./scripts/run_demo.sh
# Web http://localhost:3000  API http://localhost:8000
```

Demo logins (local only): see README.

## EnergyPlus closed-loop experiments

```bash
./scripts/setup_energyplus.sh
export ENERGYPLUS_HOME=$PWD/third_party/EnergyPlus
export ENERGYPLUS_MODEL_PATH=$PWD/building-models/sample-office/office_5zone.idf
export ENERGYPLUS_WEATHER_PATH=$PWD/building-models/weather/chicago.epw

./scripts/run_baseline.sh
./scripts/run_agent.sh
./scripts/compare_results.sh
```

Outputs:

- `results/baseline/summary.json`
- `results/agent/summary.json`
- `results/comparison/comparison.json`

If EnergyPlus is missing, experiment scripts **exit non-zero** (no silent mock success).

## Environment

Copy `.env.example` → `.env`. Important variables:

| Variable | Purpose |
|----------|---------|
| `SIMULATOR_PROVIDER` | `mock` (default) or `energyplus` |
| `ENERGYPLUS_HOME` | EnergyPlus install root |
| `ENERGYPLUS_MODEL_PATH` | IDF path |
| `ENERGYPLUS_WEATHER_PATH` | EPW path |
| `ENERGYPLUS_ALLOW_MOCK_FALLBACK` | Must be `1` to allow mock if E+ fails (debug only) |
| `AGENT_PROVIDER` | `deterministic` or `ollama` |

## Docker

```bash
docker compose --profile demo up --build
```

Compose demo profile still defaults to the mock twin unless EnergyPlus is installed in the image and env is wired.

## Clean shutdown

- Demo: Ctrl+C in the demo process; or stop Compose with `docker compose down`
- No background EnergyPlus daemon — experiments are one-shot processes

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `EnergyPlus binary not found` | `./scripts/setup_energyplus.sh` |
| `pyenergyplus.api import failed` | Ensure `ENERGYPLUS_HOME` points at extracted EnergyPlus tree |
| Actuator handle `< 0` | Confirm IDF has `Clg-SetP-Sch` Schedule:Compact |
| Dashboard savings look “too round” | Those are mock synthetic KPIs — use `results/comparison/` |
| API fails with energyplus provider | Set paths or use `SIMULATOR_PROVIDER=mock` for UI demo |
