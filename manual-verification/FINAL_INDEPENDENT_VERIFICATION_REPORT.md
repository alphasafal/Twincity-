# Final Independent Verification Report

## 1. Executive summary

Eco-Loop’s **deterministic EnergyPlus closed loop (Path A)** is real: Runtime API observations, SafetyShield-equivalent gating, `Clg-SetP-Sch` actuator writes, next-state evolution, and reproducible baseline≈421.51 vs agent≈416.00 kWh with 0 comfort violations. The **LLM path uses a real local Ollama model**, but **MCP is not actually invoked** (payload packaging only). **Dashboard KPIs match raw results when artifacts exist**, yet **EnergyPlus mode silently falls through to a mock-labeled status** if artifacts are missing. Prior **90/100 readiness is not accepted**.

**Overall: CONDITIONAL_PASS · Independent readiness score: 83/100**

## 2. Exact tested commit

- Phase 0 freeze: `61ed36cc9bc89cd37ba7a38a1ec7b4d1e12702e1`
- Experiments/docs HEAD: `589643c3557c56922b79edd886e88ea9e6833474` (docs/audit map only vs freeze)

## 3. Environment

See `00-environment/environment-summary.md` — EnergyPlus 24.1.0, Ollama 0.32.3 / `llama3.2:1b`, Python 3.12.3, Node 22.14.

## 4. What was genuinely proven

- Fresh baseline/agent EnergyPlus runs, 0 severe/fatal
- Fair identical inputs; independent metric math matches app
- Actuator write + next state for ≥5 steps
- 48 deterministic actions; comfort 0 independently
- Ollama structured proposals; unsafe 35°C rejected; Ollama-down fallback
- Dashboard API values match raw JSON in energyplus mode
- Bit-identical reproducibility on rerun
- Clean-room setup+experiments succeed

## 5. What remains unproven

- Real MCP server/tool/resource invocation on the LLM experiment path
- Real-building deployment (simulation only)
- Live co-sim dashboard ticks from EnergyPlus (UI ticker remains mock provider)

## 6. What remains mocked

- `mcp_observation_from_energyplus` simulated MCP packaging
- `SIMULATOR_PROVIDER=mock` live twin in demo UI
- Carbon as static factor estimate (documented)

## 7–9. Baseline / agent / independent %

| | Baseline | Agent | Reduction |
|--|----------|-------|-----------|
| Total kWh | 421.5057 | 415.9999 | 1.3062% |
| HVAC kWh | 13.8459 | 13.157 | 4.9755% |
| Peak kW | 19.9325 | 19.64 | 1.4675% |

## 10. Fairness

VERIFIED — see `05-fairness/`.

## 11–12. Actuator / next-state

PROVEN END TO END — `06-actuator-proof/`.

## 13. Action log

VERIFIED 48/0/0 — `07-action-log/`.

## 14. Comfort

VERIFIED 0/0 Path A — `08-comfort/`. (LLM path can violate comfort; separate.)

## 15–16. MCP / Ollama

MCP **FAILED**. Ollama **VERIFIED**.

## 17. SafetyShield

VERIFIED for experiment gate + unsafe demo + unit/matrix tests.

## 18. Failure injection

Fallback and hard-fail cases work; silent mock fallthrough is a defect.

## 19. Dashboard lineage

Real when results present; silent mock when absent.

## 20. Clean-room

PARTIALLY VERIFIED — README works; committed results + MCP overclaim remain.

## 21. Reproducibility

VERIFIED identical reruns Path A.

## 22. Software quality

23 pytest passed with PYTHONPATH; ruff debt P3.

## 23. Issues

### P0
1. MCP not actually invoked in LLM experiment
2. Silent mock labeling when DATA_MODE=energyplus and results missing

### P1
1. Path string / docs overclaim MCP
2. Committed `results/` pre-seed
3. Fallback not counted in action_counts disposition

### P2/P3
PYTHONPATH docs, demo DB/port hygiene, ruff

## 24. Fixes applied

See `16-final-evidence/fixes-applied.md` (applied after original evidence capture).

## 25. Known limitations

Simulation-only; carbon estimate; LLM metrics ≠ deterministic claimed table; UI simulator mock.

## 26. Commands that worked

```bash
./scripts/setup_energyplus.sh
./scripts/run_baseline.sh
./scripts/run_agent.sh
./scripts/compare_results.sh
./scripts/run_llm_mcp_experiment.sh
DATA_MODE=energyplus uvicorn ...  # status matches results
```

## 27. Commands that failed / problematic

```bash
# without PYTHONPATH
pytest tests/integration/test_experiment_dashboard.py  # ImportError app
# demo when :8000 held by readonly DB API
./scripts/run_demo.sh  # uvicorn errno 98; login OperationalError on stale API
```

## 28. Go/no-go

**CONDITIONAL GO** for judging **deterministic EnergyPlus savings + safety** claims.
**NO-GO** for claiming a real MCP tool loop until wired or relabeled.

## 29. Independent readiness score: **87/100** (pre-fix 83; post-fix 87)

Breakdown: {
  "energyplus_closed_loop": 23,
  "experiment_validity": 14,
  "energy_comfort": 15,
  "llm_mcp": 5,
  "safety_fallback": 13,
  "dashboard": 5,
  "clean_room": 5,
  "docs_demo": 3
}

## 30. Human verification tasks

See `MANUAL_VERIFICATION_GUIDE.md`.


---

## Phase 16 update (2026-07-25T11:09:36.750049+00:00)

Fixes applied — see `16-final-evidence/fixes-applied.md`.

- Silent mock fallthrough: **FIXED** (retested)
- MCP: upgraded from simulated dict → **in-process `twinpilot_mcp.handlers.call_tool`** (retested); remote MCP server transport still absent
- Fallback action_counts: **FIXED** (48 fallback when Ollama down)

**Post-fix independent readiness score: 87/100** (pre-fix 83/100).


---

# Remediation addendum — stdio MCP (`95a58e754e6a17ba987fa65d09401bd97f69ca43`)

Date: `2026-07-25T11:30:38.737937+00:00`

## Status

**PASS** after MCP transport remediation. Independent score **95/100**.

## What changed

1. Authoritative LLM path now uses **separate stdio MCP server** (`TWINPILOT_MCP_MODE=energyplus_experiment`).
2. Generated `results/` / `submission-evidence/` outputs **removed from Git** (gitkeeps only).
3. `./scripts/check_prerequisites.sh` verifies Ollama + model.
4. Dashboard honest no-data for `DATA_MODE=energyplus` without results.
5. README/architecture wording corrected.

## Clean-room

VERIFIED — clone at `95a58e754e6a17ba987fa65d09401bd97f69ca43` had zero result JSON; full README workflow succeeded with stdio MCP PIDs differing (`51319` ≠ `51324`).

## Historical note

Phase 9 original FAILED (simulated MCP) and later PARTIALLY VERIFIED (in-process handler) findings remain in earlier sections / `preserved-09-llm-mcp-original/` for audit continuity.
