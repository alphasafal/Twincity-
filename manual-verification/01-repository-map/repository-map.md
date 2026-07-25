# Repository Map — Independent Audit

**Tested commit:** `61ed36cc9bc89cd37ba7a38a1ec7b4d1e12702e1`  
**Captured:** 2026-07-25T10:54:48Z

| # | Item | Path | Symbol | Classification |
|---|------|------|--------|----------------|
| 1 | EnergyPlus process startup | `services/simulator/twinpilot_simulator/ep_experiment.py` | `run_experiment` → `api.runtime.run_energyplus` | real |
| 2 | Runtime API callbacks | same | `on_timestep` + `callback_end_zone_timestep_after_zone_reporting` | real |
| 3 | Variable-handle acquisition | same | `_ensure_handles` → `get_variable_handle` | real |
| 4 | Actuator-handle acquisition | same | `_ensure_handles` → `get_actuator_handle` (`Clg-SetP-Sch`) | real |
| 5 | Zone-temperature observation | same | `get_variable_value` Zone Air Temperature | real |
| 6 | Occupancy observation | same | Zone People Occupant Count | real |
| 7 | Outdoor-weather observation | same | Site Outdoor Air Drybulb Temperature | real |
| 8 | Energy/power observation | same | `_parse_results_from_csv` / meters | real (post-run CSV) |
| 9 | Baseline controller | same | `mode="baseline"` (no overrides) | real |
| 10 | Deterministic agent | same | `propose_agent_cooling_setpoint` | real |
| 11 | MCP server | `services/mcp-server/twinpilot_mcp/server.py` | FastMCP / stdio | real (separate process) |
| 12 | MCP resources/tools | `catalog.py`, `handlers.py` | HTTP to TwinPilot API | real |
| 13 | Ollama client | `scripts/llm_mcp_loop.py` `call_ollama_structured`; `providers.py` | HTTP `/api/generate` | optional |
| 14 | LLM prompt construction | `llm_mcp_loop.py` | prompt string in `call_ollama_structured` | real |
| 15 | LLM response parsing | same | `json.loads` | real |
| 16 | Structured action schema | proposed_cooling_setpoint_c JSON | real |
| 17 | SafetyShield | `twinpilot_optimizer/safety.py` + `validate_setpoint_action` | real |
| 18 | Cooling-setpoint actuator write | `set_actuator_value(handles["clg"], …)` | real |
| 19 | Fallback controller | hold last safe SP / deterministic on LLM fail | real |
| 20 | Action logging | `actions.json` | real |
| 21 | Comfort calculation | `_parse_results_from_csv` office-hours proxy | derived |
| 22 | Energy aggregation | meter sum J→kWh | real/derived |
| 23 | Peak-power calculation | max hourly facility | derived |
| 24 | Percentage reduction | `compare_summaries` / `_pct_reduction` | derived |
| 25 | Carbon estimate | kWh × 0.417 | derived |
| 26 | Backend experiment API | `experiment_store.py`, `router.py` | real |
| 27 | Dashboard API client | `apps/web/lib/api.ts` | real |
| 28 | Data-source indicator | `DataModeBanner.tsx` | real |
| 29 | Live-demo streaming | `live-demo/page.tsx` + `stream.json` | derived (replay) |
| 30 | Mock-data provider | `MockBuildingSimulator` | mocked |
| 31 | Mock-fallback config | `ENERGYPLUS_ALLOW_MOCK_FALLBACK`, `DATA_MODE` | optional |
| 32 | Baseline/agent scripts | `scripts/run_baseline.sh`, `run_agent.sh` | real |
| 33 | Evidence script | `scripts/build_submission_evidence.py` | real |

## Critical audit note (pre-runtime)

`scripts/llm_mcp_loop.py` function `mcp_observation_from_energyplus` builds a **dict shaped like** an MCP payload. Whether it starts/calls the real MCP server process must be proven in Phase 9 — source inspection alone suggests it may be **MCP-shaped local packaging**, not necessarily a live MCP stdio/HTTP session.
