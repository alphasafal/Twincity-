# AGENTS.md — TwinPilot / Eco-Loop local development

TwinPilot / Eco-Loop is a pnpm + turbo monorepo (`apps/*`, `packages/*`) plus Python
services under `services/*`. The two core dev services are:

| Service | Path | Dev command | Port |
|---------|------|-------------|------|
| API (FastAPI) | `services/api` | `source .venv/bin/activate && uvicorn app.main:app --reload --port 8000` (from `services/api`) | 8000 |
| Web (Next.js 15) | `apps/web` | `pnpm --filter @twinpilot/web dev` | 3000 |

Convenience: `make api`, `make web`, or `make demo` (API + web together). See `README.md`
and `Makefile` for the full command set.

### Startup / run caveats

- Python deps install into a repo-local `.venv` as editable installs of
  `services/{optimizer,simulator,agent,api,mcp-server}`. Always
  `source .venv/bin/activate` before running the API or pytest.
- `.env` (repo root) and `apps/web/.env.local` are gitignored. The web app needs
  `apps/web/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000` for local
  work, or `https://twinpilot.webyaar.in` when serving the public live demo.
- Default demo uses the **mock** twin: `SIMULATOR_PROVIDER=mock`,
  `AGENT_PROVIDER=deterministic` (no EnergyPlus / Ollama required).
- EnergyPlus 24.1: `./scripts/setup_energyplus.sh` → `third_party/EnergyPlus/` (gitignored).
- Ollama (optional LLM path): `OLLAMA_HOST=127.0.0.1:11434 ollama serve` then
  `ollama pull llama3.2:1b`. Export `OLLAMA_BASE_URL` / `OLLAMA_MODEL` for experiment scripts.
- `results/**` is gitignored. Regenerate with Path A/B/C scripts in `scripts/`.
- Live public demo: `./scripts/start_live_demo.sh` (requires `cloudflared tunnel login` once).

### Hello-world verification

Log in at `http://localhost:3000/login` (or https://twinpilot.webyaar.in/login) with
`manager@twinpilot.demo` / `TwinPilot-Manager-Demo!`, open Optimization, Generate plans,
then Approve and Apply — badge transitions `CANDIDATE → APPROVED → APPLIED`.
