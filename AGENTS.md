# AGENTS.md

## Cursor Cloud specific instructions

TwinPilot / Eco-Loop is a pnpm + turbo monorepo (`apps/*`, `packages/*`) plus Python
services under `services/*`. The two core dev services are:

| Service | Path | Dev command | Port |
|---------|------|-------------|------|
| API (FastAPI) | `services/api` | `source .venv/bin/activate && uvicorn app.main:app --reload --port 8000` (from `services/api`) | 8000 |
| Web (Next.js 15) | `apps/web` | `pnpm --filter @twinpilot/web dev` | 3000 |

Convenience: `make api`, `make web`, or `make demo` (API + web together). See `README.md`
and `Makefile` for the full command set; standard lint/test/build commands live there and
in each `package.json` / `pyproject.toml`, so don't duplicate them.

### Startup / run caveats (non-obvious)

- Python deps install into a repo-local `.venv` as **editable** installs of
  `services/{optimizer,simulator,agent,api,mcp-server}`. The startup update script
  refreshes this; you normally don't need to reinstall by hand. Always
  `source .venv/bin/activate` before running the API or pytest.
- `.env` (repo root) and `apps/web/.env.local` are gitignored and are created from their
  `*.example` files by the update script. The web app needs `apps/web/.env.local` with
  `NEXT_PUBLIC_API_URL=http://localhost:8000` or API calls fail.
- The default demo runs fully on the **mock** twin: `SIMULATOR_PROVIDER=mock`,
  `AGENT_PROVIDER=deterministic`. **EnergyPlus and Ollama are optional heavy dependencies**
  and are NOT installed by the update script. Only install them (`./scripts/setup_energyplus.sh`,
  Ollama) if you specifically need the real closed-loop / LLM experiment paths.
- `results/*` contain only `.gitkeep` on a fresh checkout. The `DATA_MODE=energyplus`
  dashboard payload and the integration test
  `tests/integration/test_experiment_dashboard.py::test_experiment_payload_has_real_reductions_no_synthetic`
  require first running the EnergyPlus experiments (`scripts/run_baseline.sh`,
  `scripts/run_agent.sh`). Without EnergyPlus this test fails and the dashboard shows an
  honest "no results" state — this is expected, not an environment bug.
- Ruff (current version) reports pre-existing lint errors in `services/api`
  (`F401` unused `load_comparison` import + two `RUF003` ambiguous `×` in comments).
  These already fail upstream CI on the source branch and are not caused by env setup;
  don't "fix" them as part of environment work.
- A benign `RuntimeError: unable to perform operation on <TCPTransport closed=True ...>`
  can appear in the API log when the browser navigates away and the `/ws` WebSocket closes.
  It is cosmetic and does not affect the request/response API.

### Hello-world verification

Log in at `http://localhost:3000/login` with `manager@twinpilot.demo` /
`TwinPilot-Manager-Demo!` (demo users are auto-seeded on API startup in `DEMO_MODE`), open
`Optimization`, click **Generate plans**, then **Approve** and **Apply** a plan — the badge
transitions `CANDIDATE → APPROVED → APPLIED` with a SafetyShield validation result.
