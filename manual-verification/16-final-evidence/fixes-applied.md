# Fixes Applied (Phase 16)

Report: `2026-07-25T11:09:36.750049+00:00`

Original-state evidence for Phases 0–15 remains under `manual-verification/00-*` … `15-*` and must not be overwritten.

## P0 fixes

### 1. Silent mock fallthrough when `DATA_MODE=energyplus`

- **Before:** `building_status` / `analytics_summary` returned `data_mode=mock` if experiment artifacts were missing while EnergyPlus mode was requested.
- **Fix:** `services/api/app/api/v1/router.py` — explicit `energyplus_results_unavailable` response; KPIs null; refuses mock labeling.
- **Regression:** `tests/integration/test_energyplus_no_silent_mock.py`
- **After evidence:** `16-final-evidence/status-energyplus-missing-after-fix.json` (`data_mode=energyplus`, `data_label=energyplus_results_unavailable`)

### 2. MCP packaging was simulated only

- **Before:** `mcp_observation_from_energyplus` built a local dict and logged success without calling `twinpilot_mcp`.
- **Fix:** `scripts/llm_mcp_loop.py` dispatches through `twinpilot_mcp.handlers.call_tool("get_building_state")` with an EnergyPlus-observation client (`transport=in_process`).
- **After evidence:** `16-final-evidence/mcp-dispatch-stage.jsonl` and LLM fallback recount stage logs showing `"dispatch":"twinpilot_mcp.handlers.call_tool"`.
- **Remaining limitation:** not a separate MCP stdio/HTTP server process; in-process tool dispatcher only → claim upgraded to **PARTIALLY VERIFIED**, not full remote MCP transport.

## P1 fixes

### 3. Deterministic LLM fallback not counted in action_counts

- **Before:** Ollama-down path logged `deterministic_fallback` stages but `action_counts.fallback` stayed 0 (substitute proposals counted `approved`).
- **Fix:** `ep_experiment.py` sets `disposition=fallback` when `proposal_source` starts with `deterministic_fallback`, while still applying the validated substitute setpoint.
- **After evidence:** `16-final-evidence/llm_fallback_recount/summary.json` → `fallback: 48`.

## Post-fix readiness score (independent)

**87/100** breakdown:

```json
{
  "energyplus_closed_loop": 23,
  "experiment_validity": 14,
  "energy_comfort": 15,
  "llm_mcp": 8,
  "safety_fallback": 14,
  "dashboard": 7,
  "clean_room": 5,
  "docs_demo": 4
}
```

Original pre-fix score recorded in `FINAL_INDEPENDENT_VERIFICATION_REPORT.md` was **83/100**.
