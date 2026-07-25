# Closed-Loop Code Trace

**Commit:** `61ed36cc9bc89cd37ba7a38a1ec7b4d1e12702e1`

## Path A — Deterministic EnergyPlus experiment (authoritative energy metrics)

```text
scripts/run_baseline.sh | run_agent.sh
  → twinpilot_simulator.ep_experiment.resolve_paths_from_env
  → run_experiment(ExperimentConfig)
      → _import_api → EnergyPlusAPI()
      → state_manager.new_state()
      → runtime.callback_end_zone_timestep_after_zone_reporting(on_timestep)
      → runtime.run_energyplus([-w epw, -d run_dir, idf])
         on_timestep (each zone timestep after reporting):
           → _ensure_handles: get_actuator_handle(Schedule:Compact, Schedule Value, Clg-SetP-Sch)
           → get_variable_value: outdoor, zone temps, occupancy
           → [agent only] propose_agent_cooling_setpoint(...)
           → [agent only] validate_setpoint_action(...)
           → [agent only] set_actuator_value(handles["clg"], value)
           → append actions_log / stream_frames
      → _parse_results_from_csv(eplusout.csv)
      → write summary.json, actions.json, stream.json, comfort_analysis.json
  → scripts/compare_results.sh → compare_summaries → comparison.json
  → API experiment_dashboard_payload → GET /buildings/{id}/status (DATA_MODE=energyplus)
  → apps/web DashboardPage + DataModeBanner
```

| Stage | Implementation | Class |
|-------|----------------|-------|
| Observation | Runtime API variables | real |
| Controller | deterministic propose_* | real |
| MCP | not used on Path A | n/a |
| Ollama | not used on Path A | n/a |
| Safety | validate_setpoint_action | real |
| Actuator | set_actuator_value Clg-SetP-Sch | real (runtime proof required) |
| Next state | EnergyPlus advances timesteps | real (proof required) |
| Outputs | results/* JSON + CSV | real |
| Dashboard | reads results via API | real if DATA_MODE=energyplus |

## Path B — LLM/MCP experiment script

```text
scripts/run_llm_mcp_experiment.sh → scripts/llm_mcp_loop.py
  → run_experiment(..., proposal_fn=make_proposal_fn())
      proposal_fn:
        → log energyplus_observation
        → mcp_observation_from_energyplus(obs)   # builds dict; see Phase 9
        → call_ollama_structured(mcp_payload)    # HTTP to Ollama
        → on failure: propose_agent_cooling_setpoint (deterministic fallback)
      → validate_setpoint_action → set_actuator_value
```

| Stage | Class pending Phase 9 |
|-------|------------------------|
| MCP server process | **unproven from source alone** |
| Ollama HTTP | optional / to verify |
| Safety | real |
| Actuator | same as Path A |
