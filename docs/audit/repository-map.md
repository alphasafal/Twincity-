# Repository Map — TwinPilot / Eco-Loop Building Agents

**Commit audited:** `61ed36cc9bc89cd37ba7a38a1ec7b4d1e12702e1`  
**Audit date:** 2026-07-25  
**Classification key:** `real` | `mocked` | `static` | `derived` | `optional` | `incomplete`

---

## 33-item component map

| # | Item | Absolute path | Function / class | 1-line role | Class |
|---|------|---------------|------------------|-------------|-------|
| 1 | EnergyPlus process startup | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `run_experiment` → `api.runtime.run_energyplus` | Imports `pyenergyplus`, creates state, launches EnergyPlus with IDF/EPW/`-d` run dir. | **real** |
| 2 | Runtime API callbacks | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `on_timestep` (nested in `run_experiment`); registered via `api.runtime.callback_end_zone_timestep_after_zone_reporting` | End-of-zone-timestep callback: observe → propose → validate → actuate. | **real** |
| 3 | Variable-handle acquisition | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `_ensure_handles` → `api.exchange.get_variable_handle` | Resolves outdoor drybulb, per-zone `Zone Air Temperature`, occupancy handles once API data ready. | **real** |
| 4 | Actuator-handle acquisition | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `_ensure_handles` → `api.exchange.get_actuator_handle` | Resolves `Schedule:Compact` / `Schedule Value` / `Clg-SetP-Sch` (+ heating schedule). | **real** |
| 5 | Zone-temperature observation | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `on_timestep` → `api.exchange.get_variable_value` (`temp_{zone}`) | Reads live zone air temps for SPACE1–5 each timestep. | **real** |
| 6 | Occupancy observation | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `on_timestep` → `get_variable_value` (`occ_{zone}`) | Reads `Zone People Occupant Count`, fallback `People Occupant Count` / `PEOPLE_KEYS`. | **real** |
| 7 | Outdoor-weather observation | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `on_timestep` → `get_variable_value` (`handles["outdoor"]`) | Reads `Site Outdoor Air Drybulb Temperature` / `Environment` from EPW-driven sim. | **real** |
| 8 | Energy and power observation | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `_parse_results_from_csv`, `_sum_meter_column` | Post-run sums `eplusout.csv` meters (Facility/HVAC/Cooling/… J→kWh); peak from hourly Facility. | **real** |
| 9 | Baseline controller | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `run_experiment` with `ExperimentConfig.mode="baseline"` | Leaves thermostat schedules untouched; records stream frames only. | **real** |
| 10 | Deterministic agent/controller | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `propose_agent_cooling_setpoint` | Comfort-first cooling-setpoint policy from outdoor/temps/occupancy/hour (no actuation). | **real** |
| 11 | MCP server | `/workspace/services/mcp-server/twinpilot_mcp/server.py` | `main`, `build_fastmcp`, `run_with_fastmcp`, `run_with_low_level_sdk` | stdio MCP entry; FastMCP preferred, JSON-RPC fallback. | **real** |
| 12 | MCP resources and tools | `/workspace/services/mcp-server/twinpilot_mcp/catalog.py`, `handlers.py`, `client.py` | `RESOURCES`/`TOOLS`; `read_resource`, `call_tool`; `TwinPilotClient` | Catalog + dispatch to TwinPilot REST; forecasts partly client-synthesized. | **real** (forecasts **mocked**) |
| 13 | Ollama client | `/workspace/services/agent/twinpilot_agent/providers.py`; `/workspace/scripts/llm_mcp_loop.py` | `OllamaAgentProvider._ollama`; `call_ollama_structured` | HTTP POST `/api/generate` to Ollama; used when provider/`llm_mcp` path enabled. | **optional** |
| 14 | LLM prompt construction | `/workspace/services/agent/twinpilot_agent/providers.py`; `/workspace/scripts/llm_mcp_loop.py` | `OllamaAgentProvider._prompt`; `call_ollama_structured` prompt string | Builds supervisor / HVAC-setpoint JSON-only prompts with context. | **real** |
| 15 | LLM response parsing | `/workspace/services/agent/twinpilot_agent/providers.py`; `/workspace/scripts/llm_mcp_loop.py` | `OllamaAgentProvider._parse`; `call_ollama_structured` `json.loads` | Parses JSON (regex extract + repair retry); clamps confidence. | **real** |
| 16 | Structured action schema | `/workspace/services/agent/twinpilot_agent/providers.py`; `/workspace/scripts/llm_mcp_loop.py` | `AgentPlanOutput`, `ExpectedImpact`; LLM keys `proposed_cooling_setpoint_c`/`reason`/`confidence` | Pydantic plan schema for API agent; experiment LLM uses setpoint JSON contract. | **real** |
| 17 | SafetyShield validation | `/workspace/services/optimizer/twinpilot_optimizer/safety.py`; `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `SafetyShield.validate`; `validate_setpoint_action` | API apply-path shield; E+ loop uses equivalent deterministic gate (range/rate/deadband/failures). | **real** |
| 18 | Cooling-setpoint actuator write | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `on_timestep` → `api.exchange.set_actuator_value` (`handles["clg"]`) | Writes approved (or hold) value to `Clg-SetP-Sch` each control interval. | **real** |
| 19 | Fallback controller | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py`; `/workspace/services/agent/twinpilot_agent/providers.py`; `/workspace/scripts/llm_mcp_loop.py` | `validate_setpoint_action` disposition `fallback`; `DeterministicAgentProvider`; `make_proposal_fn` → `propose_agent_cooling_setpoint` | Hold last safe SP on infra failure; LLM→deterministic proposal fallback. | **real** |
| 20 | Action logging | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `run_experiment` → `actions_log` → `actions.json` | Records proposal, disposition, blocking reasons, E+ acceptance per decision. | **real** |
| 21 | Comfort calculation | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `_parse_results_from_csv` (`comfort_analysis`) | Occupied comfort hours/degree-hours vs band using office-hours 06–20 proxy. | **derived** |
| 22 | Energy aggregation | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `_sum_meter_column`, `_parse_results_from_csv` | Aggregates Facility/HVAC/end-use meters to kWh. | **real** |
| 23 | Peak-power calculation | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `_parse_results_from_csv` (`peak_kw`) | Max of hourly Facility J × `J_TO_KWH` (avg-kW proxy per hour). | **derived** |
| 24 | Percentage-reduction calculation | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py`; `/workspace/services/api/app/services/experiment_store.py` | `compare_summaries` → nested `delta`; `_pct_reduction` | `(baseline - agent) / baseline * 100` on measured totals. | **derived** |
| 25 | Carbon estimate | `/workspace/services/simulator/twinpilot_simulator/ep_experiment.py` | `_parse_results_from_csv` (`carbon_estimate_kg`); `DEFAULT_CARBON_KG_PER_KWH` | `total_energy_kwh * 0.417`; labeled estimate, not live grid. | **derived** |
| 26 | Backend experiment-data API | `/workspace/services/api/app/services/experiment_store.py`; `/workspace/services/api/app/api/v1/router.py` | `experiment_dashboard_payload`, `load_*`; `building_status`, `experiments_comparison`, `experiments_stream`, `experiments_actions`, `analytics_summary` | Serves `results/*` JSON when `DATA_MODE=energyplus`. | **real** |
| 27 | Dashboard API client | `/workspace/apps/web/lib/api.ts`; `/workspace/apps/web/lib/hooks.ts` | `apiFetch`, `api.getBuildingStatus`, `api.experimentStream`, …; `useLiveBuilding` | Authenticated fetch + polling/WS for dashboard status. | **real** |
| 28 | Dashboard data-source indicator | `/workspace/apps/web/components/DataModeBanner.tsx`; used in `/workspace/apps/web/app/dashboard/page.tsx` | `DataModeBanner`; `DashboardPage` | Shows `DATA_MODE=` and visible source; warns if synthetic multiplier. | **real** |
| 29 | Live-demo streaming logic | `/workspace/apps/web/app/live-demo/page.tsx`; `/workspace/services/api/app/api/v1/router.py` | `LiveDemoPage`; `experiments_stream` ← `load_stream_frames` | Accelerated playback of recorded `stream.json` frames (~3 min), not live E+. | **derived** |
| 30 | Mock-data provider | `/workspace/services/simulator/twinpilot_simulator/mock.py`; `/workspace/services/api/app/services/runtime.py` | `MockBuildingSimulator`; `RuntimeHub` when `SIMULATOR_PROVIDER=mock` | Deterministic digital-twin dynamics for interactive API control loop. | **mocked** |
| 31 | Mock-fallback configuration | `/workspace/services/api/app/core/config.py`; `/workspace/services/simulator/twinpilot_simulator/energyplus.py`; `.env` / `.env.example` | `Settings` (`simulator_provider`, `data_mode`, …); `EnergyPlusAdapter` / `_env_flag("ENERGYPLUS_ALLOW_MOCK_FALLBACK")` | Opt-in mock fallback; default hackathon `DATA_MODE=energyplus`, `SIMULATOR_PROVIDER=mock`. | **optional** |
| 32 | Baseline and agent scripts | `/workspace/scripts/run_baseline.sh`; `/workspace/scripts/run_agent.sh` | shell → inline Python calling `resolve_paths_from_env` + `run_experiment` | Fail-loud E+ harness writing `results/{baseline,agent}/summary.json`. | **real** |
| 33 | Evidence-generation script | `/workspace/scripts/build_submission_evidence.py` | `main`, `write_csv`, `architecture_png` | Assembles `submission-evidence/` CSVs/JSON/logs from `results/*`. | **real** |

### Related adapters / config (not separate numbered items)

| Path | Symbol | Note |
|------|--------|------|
| `/workspace/services/simulator/twinpilot_simulator/energyplus.py` | `EnergyPlusAdapter` | Interactive API bridge; `initialize` probes via `run_experiment(mode="baseline")`; `apply_action` does **not** re-inject actuators mid-run (**incomplete** for live E+ UI loop). |
| `/workspace/services/api/app/services/runtime.py` | `RuntimeHub._control_loop` / `_run_cycle_sync` | Default mock-stepping UI loop. |
| `/workspace/scripts/compare_results.sh` | shell → `compare_summaries` | Writes `results/comparison/comparison.json`. |
| `/workspace/scripts/llm_mcp_loop.py` | `main`, `make_proposal_fn` | Optional E+→MCP-shaped obs→Ollama→Safety→actuator proof path. |
| `/workspace/scripts/run_llm_mcp_experiment.sh` | shell wrapper | Invokes `llm_mcp_loop.py`. |

---

## Architecture (measured vs interactive)

```text
MEASURED CLOSED LOOP (scripts)
  run_baseline.sh / run_agent.sh
    → ep_experiment.run_experiment
    → EnergyPlus Runtime API + Clg-SetP-Sch actuator
    → results/{baseline,agent}/*.json
    → experiment_store → API → Dashboard (DATA_MODE=energyplus)

INTERACTIVE API LOOP (default)
  RuntimeHub + MockBuildingSimulator (SIMULATOR_PROVIDER=mock)
    → SafetyShield on apply
    → WebSocket / status KPIs (mock twin; no invented ×1.12 savings)
```

---

## Entry points

| Surface | Entry | Command |
|---------|-------|---------|
| API | `/workspace/services/api/app/main.py` | `make api` |
| Web | `/workspace/apps/web` | `make web` / `make demo` |
| MCP | `/workspace/services/mcp-server/twinpilot_mcp/__main__.py` → `server.main` | `python -m twinpilot_mcp` |
| Control loop | `RuntimeHub` in `runtime.py` | API lifespan |
| Experiments | `scripts/run_baseline.sh`, `run_agent.sh`, `compare_results.sh` | Phase-3 harness |

---

## Env knobs (audit-critical)

| Variable | Where read | Effect |
|----------|------------|--------|
| `ENERGYPLUS_HOME` / `MODEL_PATH` / `WEATHER_PATH` | `resolve_paths_from_env`, `Settings`, scripts | Real E+ inputs |
| `SIMULATOR_PROVIDER` | `Settings` → `RuntimeHub` | `mock` (default) vs `energyplus` adapter |
| `ENERGYPLUS_ALLOW_MOCK_FALLBACK` | `EnergyPlusAdapter` | Opt-in mock if E+ unavailable; else raise |
| `DATA_MODE` | `Settings.data_mode` → `building_status` / analytics | `energyplus` serves `results/*`; `mock` serves twin |
| `AGENT_PROVIDER` | `Settings` → `get_agent_provider` | `deterministic` \| `ollama` |
| `OLLAMA_BASE_URL` / `OLLAMA_MODEL` | agent + `llm_mcp_loop` | Optional LLM |
| `RESULTS_DIR` | `experiment_store.results_root` | Artifact root override |
