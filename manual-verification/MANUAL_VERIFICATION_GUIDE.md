# Manual Verification Guide (for the project owner)

Audited tip commit: run `git rev-parse HEAD` (remediation series includes `9085cbc` / `1b6a045` / `95a58e7`).  
Score after stdio MCP remediation: **95/100 PASS** — see `verification-summary.json`.

For each item: run the command, check the file/field, tick the box.

## [ ] Exact commit confirmed
- Command: `git rev-parse HEAD`
- Success: matches the branch tip you intend to judge
- Open: terminal output

## [ ] Prerequisites pass
- Command: `./scripts/check_prerequisites.sh`
- Success: ends with `RESULT: PASS`
- Failure: lists FAIL lines (e.g. missing `ollama pull llama3.2:1b`)

## [ ] Fresh clone has no pre-baked results
- Command: `git ls-files results/`
- Success: only `.gitkeep` paths (five lines)
- Also: `find results -name '*.json' | wc -l` is `0` on a fresh clone before experiments

## [ ] Fresh baseline created
- Command: `./scripts/run_baseline.sh`
- Success: exit 0; `results/baseline/summary.json` has new `timestamp_utc` and `total_energy_kwh` ≈ 421.51
- Open: `results/baseline/summary.json` → `total_energy_kwh`

## [ ] Fresh agent result created
- Command: `./scripts/run_agent.sh`
- Success: `total_energy_kwh` ≈ 416.00; `action_counts.approved` = 48
- Open: `results/agent/summary.json`

## [ ] IDF and EPW match
- Command: `sha256sum building-models/sample-office/office_5zone.idf building-models/weather/chicago.epw`
- Compare to paths inside both summaries under `identical_inputs`

## [ ] Occupancy and simulation period match
- Open both summaries → `identical_inputs.run_period` and `occupancy_schedule` must be identical text

## [ ] Actuator write personally observed
- Open: `results/agent/actions.json`
- Find `"energyplus_actuator_written": true` and `"energyplus_action_accepted": true`
- Confirm some rows change `applied_cooling_setpoint_c` vs `previous_cooling_setpoint_c`

## [ ] Following EnergyPlus state personally observed
- Open: `manual-verification/06-actuator-proof/actuator-runtime-trace.csv`
- Check `next_sim_time` and `next_avg_zone_temp_c` change after an action

## [ ] Action records counted
- Command: `python3 -c "import json; a=json.load(open('results/agent/actions.json')); print(len(a), sum(1 for x in a if x['disposition']=='approved'))"`
- Success: `48 48`

## [ ] Comfort independently checked
- Open: `results/agent/comfort_analysis.json`
- Success: 0 violation hours / 0 degree-hours for the **deterministic** agent

## [ ] Ollama process personally observed
- Command: `curl -s http://127.0.0.1:11434/api/tags`
- Then: `./scripts/run_llm_mcp_experiment.sh`
- Open: `results/llm_mcp/stage_log.jsonl` — `"provider": "ollama"` and `"ok": true`

## [ ] Separate MCP server process personally observed
- While `./scripts/run_llm_mcp_experiment.sh` is running: `ps aux | rg 'twinpilot_mcp|TWINPILOT_MCP_MODE'`
- Success: a **child** Python process appears (different PID from the experiment script)
- After run, open `results/llm_mcp/summary.json`:
  - `mcp_transport` = `stdio`
  - `mcp_pids_differ` = `true`
  - `mcp_client_pid` ≠ `mcp_server_pid`
- Also open `manual-verification/mcp-transport/mcp-runtime-trace.jsonl` for `initialize_ok`, `tools_list`, `tools_call_request`

## [ ] Authoritative path is not in-process handler dispatch
- Command: `rg -n "from twinpilot_mcp.handlers import call_tool|open_energyplus_mcp_session" scripts/llm_mcp_loop.py`
- Success: uses `open_energyplus_mcp_session`; **no** `handlers import call_tool`

## [ ] Unsafe action personally rejected
- Open: `results/llm_mcp/stage_log.jsonl`
- Find `"stage": "safety_shield_rejects_unsafe"` with `"proposed": 35.0` and `"approved": false`

## [ ] LLM failure personally triggered
- Command: `OLLAMA_BASE_URL=http://127.0.0.1:1 RESULTS_LLM_DIR=/tmp/llm_fail_test ./scripts/run_llm_mcp_experiment.sh`
- Open stage log: `"ok": false` and `"stage": "deterministic_fallback"`

## [ ] Deterministic fallback personally observed
- Same as above — simulation still completes; fallback stages exist

## [ ] Dashboard no-data state (before experiments on a clean tree)
- With empty `results/*/summary.json` and `DATA_MODE=energyplus`, open `/dashboard` or status API
- Success text: **No EnergyPlus experiment results found. Run the baseline and agent experiment scripts first.**
- Must show `data_mode=energyplus`, **not** mock KPIs

## [ ] Dashboard API response inspected (after experiments)
- `DATA_MODE=energyplus ./scripts/run_demo.sh` (or API on :8000)
- Login, GET `/api/v1/buildings/{id}/status`
- Success: `"data_mode":"energyplus"`, `"synthetic_multiplier_applied":false`, totals match `results/*`

## [ ] Dashboard values matched raw files
- Compare status `experiment.baseline.total_energy_kwh` to `results/baseline/summary.json`

## [ ] Backend-disconnection behaviour observed
- Stop API; refresh — should error, not show fake success

## [ ] No silent mock mode observed
- `DATA_MODE=energyplus` + missing results → no-data (above)
- Mock only when explicitly `DATA_MODE=mock`

## [ ] Clean clone successfully executed
- `git clone <repo> /tmp/tp-clean && cd /tmp/tp-clean`
- `./scripts/setup.sh && ./scripts/check_prerequisites.sh && ./scripts/setup_energyplus.sh`
- `./scripts/run_baseline.sh && ./scripts/run_agent.sh && ./scripts/compare_results.sh`
- Success: exit 0 everywhere; new summary timestamps; `git ls-files results/` still only gitkeeps in the clone history
