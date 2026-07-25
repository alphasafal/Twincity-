# AGENTS.md

## Cursor Cloud specific instructions

TwinPilot / Eco-Loop is a single product in a pnpm+Turbo monorepo (JS workspace under `apps/*`, `packages/*`) plus editable Python packages under `services/*`. Standard commands live in the `Makefile` and `README.md` — prefer those. Notes below are the non-obvious things.

### Services (dev scope)
- Core end-to-end stack = FastAPI API (`:8000`) + Next.js web (`:3000`) + file-based SQLite. Defaults to `SIMULATOR_PROVIDER=mock` and `AGENT_PROVIDER=deterministic`, so no EnergyPlus / Ollama / Postgres is needed to run and demo the app.
- `optimizer`, `simulator`, and `agent` under `services/` are libraries imported in-process by the API, not standalone servers. Only the API and web are long-running network servers. The MCP server (`services/mcp-server`) is a stdio subprocess used only by experiment scripts.

### Running
- Activate the Python env with `source .venv/bin/activate` before running API/pytest.
- API: `make api` (uvicorn on `:8000`). Web: `make web` (Next.js on `:3000`). Both together: `make demo`.
- The web dev server reads `apps/web/.env.local` (`NEXT_PUBLIC_API_URL=http://localhost:8000`); the API reads root `.env`. Both are created from `*.example` by the setup script.
- Demo login (dev only): `manager@twinpilot.demo` / `TwinPilot-Manager-Demo!` (also `admin`/`operator`/`viewer`, see `README.md`). The API auto-seeds these users and a demo building on startup.

### Expected honest no-data state (not a bug)
- `.env` ships `DATA_MODE=energyplus`, so the dashboard shows a banner: "No EnergyPlus experiment results found. Run the baseline and agent experiment scripts first." until experiments are generated. This is intentional — the app never silently shows mock KPIs in energyplus mode. The live power ticker still uses the mock twin. For mock KPIs, run with `DATA_MODE=mock`.

### Testing
- Lint/test/build commands are defined in the `Makefile` (`make lint`, `make test`) and `README.md`. API pytest runs from `services/api`; integration tests need `PYTHONPATH` spanning `services/api:services/optimizer:services/simulator:services/agent` (see the `Makefile` `test` target).
- `tests/integration/test_experiment_dashboard.py::test_experiment_payload_has_real_reductions_no_synthetic` fails in a base setup because it requires generated EnergyPlus results under `results/*` (only `.gitkeep` is committed). Generating them needs EnergyPlus 24.1 (`./scripts/setup_energyplus.sh` + `./scripts/run_baseline.sh` + `./scripts/run_agent.sh`). Treat this failure as expected unless you have specifically set up the EnergyPlus experiment path.
- Web e2e uses Playwright: run `pnpm --filter @twinpilot/web test:e2e:install` before `test:e2e`.

### Gotchas
- `python3 -m venv` requires the `python3.12-venv` system package; without it venv creation fails with an `ensurepip is not available` error. The setup script does not install system packages.
- If `.venv` was created by a failed/interrupted run, delete it (`rm -rf .venv`) and re-run setup — a partial venv has no `bin/activate`.
- pnpm reports "Ignored build scripts: sharp, unrs-resolver". This is fine; the web dev server and typecheck/lint work without them. Do not run the interactive `pnpm approve-builds`.
