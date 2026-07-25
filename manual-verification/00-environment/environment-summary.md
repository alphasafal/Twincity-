# Environment Summary — Phase 0 Freeze

| Field | Value |
|-------|-------|
| Captured at (UTC) | `2026-07-25T10:54:24Z` |
| Working directory | `/workspace` |
| OS | Ubuntu 24.04.4 LTS (Noble) |
| Kernel | Linux 6.12.94+ |
| Architecture | x86_64 |
| Disk (`/workspace` overlay) | 252G total, ~225G free |
| Python | 3.12.3 (`/workspace/.venv/bin/python3`) |
| Node.js | v22.14.0 |
| pnpm | 10.33.3 |
| npm | 10.9.7 |
| Docker | **not found** |
| EnergyPlus path | `/workspace/third_party/EnergyPlus/energyplus` |
| EnergyPlus version | **24.1.0-9d7789a3ac** |
| Ollama version | 0.32.3 |
| Ollama models | `llama3.2:1b` (baf6a787fdff, 1.3 GB) |
| Git branch | `cursor/ecolooop-energyplus-audit-b6b3` |
| Git commit | **`61ed36cc9bc89cd37ba7a38a1ec7b4d1e12702e1`** |
| Commit subject | Final hackathon hardening: real dashboard DATA_MODE, LLM-MCP, comfort-zero |
| Commit date | 2026-07-25 10:46:24 +0000 |
| Tree clean? | **Yes for tracked files**; untracked `manual-verification/` created by this audit |
| Remotes | `origin` → github.com/alphasafal/Twincity- |
| Dashboard startup | `./scripts/run_demo.sh` (documented) |
| Experiment startup | `./scripts/run_baseline.sh`, `./scripts/run_agent.sh`, `./scripts/compare_results.sh` |

## Environment variable names present (values not logged)

`ENERGYPLUS_HOME`, `ENERGYPLUS_MODEL_PATH`, `ENERGYPLUS_WEATHER_PATH`, `PYTHONPATH`, `PATH`, plus Cursor agent internals.

## Policy for this audit

- No application code modifications until Phases 0–15 original-state evidence is collected.
- Evidence directory: `manual-verification/`.
- Tested commit frozen: `61ed36cc9bc89cd37ba7a38a1ec7b4d1e12702e1`.


## Commit drift note

After Phase 0 freeze at `61ed36c`, HEAD advanced to `589643c` (doc/map commit). Fresh experiments and LLM run executed with HEAD=`589643c`. Application experiment code diff vs freeze:

 docs/audit/closed-loop-code-trace.md | 222 ++++++++++++++++++++++++++++++++
 docs/audit/repository-map.md         | 241 ++++++++++++-----------------------
 2 files changed, 302 insertions(+), 161 deletions(-)
