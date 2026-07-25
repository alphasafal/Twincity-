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
  `AGENT_PROVIDER=deterministic`, and needs neither EnergyPlus nor Ollama.
- **EnergyPlus 24.1 and Ollama are heavy deps installed once (via `./scripts/setup_energyplus.sh`
  and the ollama.com installer) and persisted in the VM snapshot** — they are intentionally
  NOT in the startup update script (large download + system-level install). EnergyPlus lives
  at `third_party/EnergyPlus/` (gitignored). If a future VM lacks them, reinstall with those
  same scripts (`sudo apt-get install -y zstd` is required before the ollama installer).
- **Ollama has no systemd here**, so start it manually before LLM/prereq checks:
  `OLLAMA_HOST=127.0.0.1:11434 ollama serve` (run in a tmux/background session). The model
  `llama3.2:1b` is pulled; re-pull with `ollama pull llama3.2:1b` if missing. Export
  `OLLAMA_BASE_URL=http://127.0.0.1:11434` and `OLLAMA_MODEL=llama3.2:1b` for the experiment scripts.
- `results/**` is gitignored (never commit generated results). Regenerate with
  `scripts/run_baseline.sh` + `scripts/run_agent.sh` + `scripts/compare_results.sh` (Path A),
  `scripts/run_llm_mcp_experiment.sh` (Path B), `scripts/run_hybrid_supervisory_experiment.sh`
  (Path C). Each EnergyPlus *agent* run takes ~3–5 min; LLM paths are slower (per-hour Ollama
  calls). The `DATA_MODE=energyplus` API/dashboard reads `results/*` live — no API restart
  needed after regenerating. `tests/integration/test_experiment_dashboard.py` requires Path A
  results to exist. `./scripts/check_prerequisites.sh` and `./scripts/final_smoke_test.sh`
  validate the whole setup.
- The LLM/MCP experiment scripts overwrite tracked trace logs under
  `manual-verification/mcp-transport/*.jsonl`; `git checkout -- manual-verification/` to
  discard that re-run noise before committing.
- A benign `RuntimeError: unable to perform operation on <TCPTransport closed=True ...>`
  can appear in the API log when the browser navigates away and the `/ws` WebSocket closes.
  It is cosmetic and does not affect the request/response API.

### Hello-world verification

Log in at `http://localhost:3000/login` with `manager@twinpilot.demo` /
`TwinPilot-Manager-Demo!` (demo users are auto-seeded on API startup in `DEMO_MODE`), open
`Optimization`, click **Generate plans**, then **Approve** and **Apply** a plan — the badge
transitions `CANDIDATE → APPROVED → APPLIED` with a SafetyShield validation result.
