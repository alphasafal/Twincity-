# Closed-Loop Code Trace — EnergyPlus → Dashboard

**Commit audited:** `61ed36cc9bc89cd37ba7a38a1ec7b4d1e12702e1`  
**Primary harness:** `./scripts/run_baseline.sh && ./scripts/run_agent.sh && ./scripts/compare_results.sh`  
**Optional LLM path:** `./scripts/run_llm_mcp_experiment.sh` → `/workspace/scripts/llm_mcp_loop.py`

---

## A. Measured EnergyPlus closed loop (agent experiment)

Exact call chain with function names:

```text
1. ENTRY
   scripts/run_agent.sh
     → resolve_paths_from_env(output_dir)
     → run_experiment(ExperimentConfig(mode="agent"))

2. PROCESS STARTUP
   run_experiment
     → _import_api(paths.energyplus_home)          # pyenergyplus.api.EnergyPlusAPI
     → api.state_manager.new_state()
     → api.runtime.callback_end_zone_timestep_after_zone_reporting(state, on_timestep)
     → api.runtime.run_energyplus(state, ["-w", epw, "-d", run_dir, idf])

3. HANDLE ACQUISITION (first ready timestep)
   on_timestep
     → _ensure_handles(state_arg)
         → api.exchange.api_data_fully_ready
         → api.exchange.get_actuator_handle(..., "Clg-SetP-Sch")   # handles["clg"]
         → api.exchange.get_actuator_handle(..., "Htg-SetP-Sch")   # handles["htg"]
         → api.exchange.get_variable_handle(..., "Site Outdoor Air Drybulb Temperature")
         → api.exchange.get_variable_handle(..., "Zone Air Temperature", zone)
         → api.exchange.get_variable_handle(..., "Zone People Occupant Count" | "People Occupant Count")

4. OBSERVATION (each post-warmup timestep)
   on_timestep
     → api.exchange.warmup_flag / month / day_of_month / hour / minutes
     → api.exchange.get_variable_value(handles["outdoor"])         # outdoor weather
     → api.exchange.get_variable_value(handles[f"temp_{z}"])       # zone temps
     → api.exchange.get_variable_value(handles[f"occ_{z}"])        # occupancy
     → observations.append(obs)  # source="energyplus_runtime_api"

5. PROPOSAL (once per control_interval_minutes; default hourly)
   on_timestep
     → config.proposal_fn(...)   # optional LLM/MCP (llm_mcp_loop.make_proposal_fn)
       OR
     → propose_agent_cooling_setpoint(
           outdoor_c, zone_temps, occupancy,
           current_cooling_setpoint, limits, hour
       )
     → returns (proposed, reason, confidence)

6. SAFETY GATE
   on_timestep
     → validate_setpoint_action(
           proposed, current, heating_setpoint, limits,
           confidence, sensors_healthy, data_age_seconds,
           manual_override, llm_timed_out, mcp_failed
       )
     → (approved, blocking_reasons, disposition)
       disposition ∈ {approved, rejected, fallback}

7. ACTUATOR WRITE
   on_timestep
     if approved:
       api.exchange.set_actuator_value(state, handles["clg"], proposed)
     else:
       api.exchange.set_actuator_value(state, handles["clg"], current_cooling)  # hold safe
     → actions_log.append(action_record)
     → stream_frames.append(...)   # if record_stream

8. ENERGYPLUS ADVANCES
   (EnergyPlus physics continues; next callback sees new state)

9. POST-RUN METRICS
   run_experiment (after rc==0)
     → _parse_results_from_csv(run_dir, carbon_kg_per_kwh, limits, actions_log)
         → _sum_meter_column(...)           # energy aggregation
         → peak_kw from hourly Facility     # peak-power (derived)
         → comfort_analysis                 # comfort (office-hours proxy)
         → carbon_estimate_kg = total_kwh * factor
     → write summary.json, actions.json, comfort_analysis.json, stream.json

10. COMPARISON
    scripts/compare_results.sh
      → compare_summaries(baseline, agent)
          → nested delta() / percent_reduction
      → results/comparison/comparison.json
```

### Baseline-only difference

```text
run_experiment(mode="baseline")
  → on_timestep observes + optional stream_frames
  → returns early before proposal/safety/actuator (IDF schedules untouched)
```

---

## B. Optional LLM-via-MCP path (`llm_mcp_loop.py`)

```text
main()
  → run_experiment(mode="baseline")
  → run_experiment(mode="agent", proposal_fn=make_proposal_fn(), agent_provider="llm_mcp")

make_proposal_fn() / proposal_fn
  → log_stage("energyplus_observation", ...)
  → mcp_observation_from_energyplus(obs)     # MCP-shaped payload (not live MCP stdio)
      → log_stage("mcp_resource_tool", ...)
  → call_ollama_structured(mcp_payload)
      → urllib → Ollama /api/generate
      → parse proposed_cooling_setpoint_c, confidence
  if Ollama fails:
      → propose_agent_cooling_setpoint(...)   # deterministic fallback
  → returns into on_timestep → validate_setpoint_action → set_actuator_value

Post-proof:
  → validate_setpoint_action(proposed=35.0, ...)  # must reject / not bypass
```

Note: `mcp_observation_from_energyplus` **simulates** MCP resource/tool JSON shape; production MCP is `twinpilot_mcp.handlers.read_resource` / `call_tool` → `TwinPilotClient` → API.

---

## C. Artifact → API → Dashboard

```text
results/baseline/summary.json
results/agent/summary.json
results/agent/actions.json
results/agent/stream.json
results/comparison/comparison.json
        │
        ▼
experiment_store.load_baseline / load_agent / load_comparison
experiment_store.load_actions / load_stream_frames / load_comfort_analysis
experiment_store.experiment_dashboard_payload(scenario)
        │
        ▼
router.building_status          # DATA_MODE=energyplus → KPIs from experiment payload
router.analytics_summary
router.experiments_comparison
router.experiments_stream       # frames for live-demo
router.experiments_actions
        │
        ▼
apps/web/lib/api.ts
  api.getBuildingStatus / api.experimentStream / api.experimentComparison
apps/web/lib/hooks.ts
  useLiveBuilding → poll + WS
        │
        ▼
apps/web/app/dashboard/page.tsx   DashboardPage
  → DataModeBanner(dataMode, dataSourceVisible, syntheticMultiplierApplied)
  → KpiCard / comparison from data.experiment

apps/web/app/live-demo/page.tsx   LiveDemoPage
  → api.experimentStream → setInterval frame advance (~180s playback)
  → DataModeBanner(dataMode="energyplus", dataSourceVisible="results/agent/stream.json")
```

`Settings.data_mode` (`/workspace/services/api/app/core/config.py`) gates energyplus vs mock in `building_status` / `analytics_summary`.

---

## D. Interactive API control loop (separate from measured E+ harness)

```text
main.lifespan
  → RuntimeHub.initialize_from_db
      → MockBuildingSimulator.initialize  OR  EnergyPlusAdapter.initialize
  → RuntimeHub.start_background
      → RuntimeHub._control_loop
          → RuntimeHub.run_cycle → _run_cycle_sync
              → MockBuildingSimulator.step / get_state
              → planner / SafetyShield.validate (on apply paths)
              → publish WebSocket events

API apply path (not E+ Runtime actuator):
  router.apply_plan
    → SafetyShield.validate(ProposedAction, ValidationContext)
    → RuntimeHub / simulator.apply_action
```

**Gap:** `EnergyPlusAdapter.apply_action` records pending setpoints only; full `set_actuator_value` injection is executed inside `ep_experiment.on_timestep` during harness runs. Default `.env` uses `SIMULATOR_PROVIDER=mock` for the 5s UI loop while dashboard KPIs use `DATA_MODE=energyplus` artifacts.

---

## E. Stage → function quick index

| Stage | Exact symbols |
|-------|----------------|
| Startup | `run_experiment`, `_import_api`, `api.runtime.run_energyplus` |
| Callback register | `api.runtime.callback_end_zone_timestep_after_zone_reporting` |
| Handles | `_ensure_handles`, `get_variable_handle`, `get_actuator_handle` |
| Observe | `on_timestep`, `get_variable_value` |
| Propose | `propose_agent_cooling_setpoint` / `proposal_fn` / `call_ollama_structured` |
| Validate | `validate_setpoint_action` (E+); `SafetyShield.validate` (API) |
| Actuate | `set_actuator_value` on `handles["clg"]` |
| Log | `actions_log` → `actions.json`; `stream_frames` → `stream.json` |
| Aggregate | `_parse_results_from_csv`, `_sum_meter_column`, `compare_summaries` |
| Serve | `experiment_dashboard_payload`, `building_status`, `experiments_stream` |
| Display | `DashboardPage`, `LiveDemoPage`, `DataModeBanner` |

---

## F. Field provenance (code-backed)

| Signal | Function | Source | Class |
|--------|----------|--------|-------|
| Zone temp | `on_timestep` | E+ `Zone Air Temperature` | real |
| Occupancy | `on_timestep` | E+ people count vars | real |
| Outdoor | `on_timestep` | E+ site drybulb / EPW | real |
| Energy | `_sum_meter_column` | `eplusout.csv` meters | real |
| Peak power | `_parse_results_from_csv` | hourly Facility J→kW | derived |
| Comfort | `_parse_results_from_csv` | temps vs band + hours proxy | derived |
| Carbon | `_parse_results_from_csv` | `kWh * DEFAULT_CARBON_KG_PER_KWH` | derived |
| % reduction | `compare_summaries` / `_pct_reduction` | arithmetic on summaries | derived |
| Live-demo power field | stream frame `energy_power_kw` | always `None` in harness | incomplete |
