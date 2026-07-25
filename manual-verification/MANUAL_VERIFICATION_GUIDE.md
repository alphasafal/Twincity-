# Manual Verification Guide (for the project owner)

Report commit: `589643c3557c56922b79edd886e88ea9e6833474` · Generated `2026-07-25T11:08:07.584946+00:00`

For each item: run the command, check the file/field, tick the box.

## [ ] Exact commit confirmed
- Command: `git rev-parse HEAD`
- Success: prints `589643c3557c56922b79edd886e88ea9e6833474` (or your audited SHA)
- Failure: different hash — re-run audit on that commit
- Open: terminal output

## [ ] Fresh baseline created
- Command: `./scripts/run_baseline.sh`
- Success: exit 0; `results/baseline/summary.json` has new `timestamp_utc` and `total_energy_kwh` ≈ 421.51
- Failure: non-zero exit or missing summary
- Open: `results/baseline/summary.json` → `total_energy_kwh`

## [ ] Fresh agent result created
- Command: `./scripts/run_agent.sh`
- Success: `total_energy_kwh` ≈ 416.00; `action_counts.approved` = 48
- Open: `results/agent/summary.json`

## [ ] IDF and EPW match
- Command: `sha256sum building-models/sample-office/office_5zone.idf building-models/weather/chicago.epw`
- Compare to paths inside both summaries under `identical_inputs`
- Open: `results/baseline/summary.json` and `results/agent/summary.json`

## [ ] Occupancy and simulation period match
- Open both summaries → `identical_inputs.run_period` and `occupancy_schedule` must be identical text

## [ ] Actuator write personally observed
- Open: `results/agent/actions.json`
- Find a row with `"energyplus_actuator_written": true` and `"energyplus_action_accepted": true`
- Confirm `"applied_cooling_setpoint_c"` differs from `"previous_cooling_setpoint_c"` on some rows

## [ ] Following EnergyPlus state personally observed
- Open: `manual-verification/06-actuator-proof/actuator-runtime-trace.csv`
- Check `next_sim_time` and `next_avg_zone_temp_c` change after an action

## [ ] Action records counted
- Command: `python3 -c "import json; a=json.load(open('results/agent/actions.json')); print(len(a), sum(1 for x in a if x['disposition']=='approved'))"`
- Success: `48 48`

## [ ] Comfort independently checked
- Open: `results/agent/comfort_analysis.json` and `manual-verification/08-comfort/comfort-verification.md`
- Success: 0 violation hours / 0 degree-hours

## [ ] Ollama process personally observed
- Command: `curl -s http://127.0.0.1:11434/api/tags`
- Then: `./scripts/run_llm_mcp_experiment.sh`
- Open: `results/llm_mcp/stage_log.jsonl` — lines with `"provider": "ollama"` and `"ok": true`

## [ ] MCP invocation personally observed
- Command: `rg -n "Simulate MCP|twinpilot_mcp" scripts/llm_mcp_loop.py`
- Expect: docstring says **Simulate MCP**; no live MCP server required
- Also: `ps aux | rg twinpilot_mcp` during LLM run should show **nothing** (before any fix)
- This claim should be treated as **not proven** unless you see a real MCP server call after fixes

## [ ] Unsafe action personally rejected
- Open: `results/llm_mcp/stage_log.jsonl`
- Find `"stage": "safety_shield_rejects_unsafe"` with `"proposed": 35.0` and `"approved": false`

## [ ] LLM failure personally triggered
- Command: `OLLAMA_BASE_URL=http://127.0.0.1:1 RESULTS_LLM_DIR=/tmp/llm_fail_test ./scripts/run_llm_mcp_experiment.sh` (or `python3 scripts/llm_mcp_loop.py` with those env vars)
- Open stage log: `"ok": false` and `"stage": "deterministic_fallback"`

## [ ] Deterministic fallback personally observed
- Same as above — confirm simulation still completes and fallback stages exist

## [ ] Dashboard API response inspected
- Start API with `DATA_MODE=energyplus`, login, GET `/api/v1/buildings/{id}/status`
- Success fields: `"data_mode":"energyplus"`, `"synthetic_multiplier_applied":false`, experiment totals match files

## [ ] Dashboard values matched raw files
- Compare status `experiment.baseline.total_energy_kwh` to `results/baseline/summary.json`

## [ ] Backend-disconnection behaviour observed
- Stop API; refresh dashboard/API call — should error, not show fake success

## [ ] No silent mock mode observed
- Temporarily move `results/baseline` aside with `DATA_MODE=energyplus`
- **Before fix:** status may show `"data_mode":"mock"` — that is a defect
- **After fix:** should show energyplus unavailable / error, not mock KPIs disguised as success

## [ ] Clean clone successfully executed
- `git clone <repo> /tmp/tp-clean && cd /tmp/tp-clean && ./scripts/setup.sh && ./scripts/setup_energyplus.sh && ./scripts/run_baseline.sh`
- Success: exit 0 and new summary timestamps
