# Claim Evidence Matrix

Tested commit HEAD: `589643c3557c56922b79edd886e88ea9e6833474` · Phase0 freeze: `61ed36cc9bc89cd37ba7a38a1ec7b4d1e12702e1` · Report: `2026-07-25T11:08:07.584946+00:00`

| Claim | Source-code evidence | Runtime evidence | Independent check | Status |
|---|---|---|---|---|
| EnergyPlus runs | ep_experiment.run_experiment | eplusout + err 0 severe | fresh timestamps/checksums | **VERIFIED** |\n| Baseline generated fresh | run_baseline.sh | 03-baseline/fresh-run | mtime+sha | **VERIFIED** |\n| Agent generated fresh | run_agent.sh | 04-agent/fresh-run | mtime+sha | **VERIFIED** |\n| Inputs identical | identical_inputs + fairness md | same idf/epw hashes | 05-fairness | **VERIFIED** |\n| Actuator is written | set_actuator_value Clg-SetP-Sch | actuator-runtime-trace.csv written=True | next SP matches | **VERIFIED** |\n| Next state is returned | callback stream.json | trace next_* columns | 5+ consecutive | **VERIFIED** |\n| 48 actions are genuine | actions.json logger | independent count 48 | 07-action-log | **VERIFIED** |\n| Comfort is zero | ep comfort calc | independent CSV recompute 0 | 08-comfort | **VERIFIED** |\n| MCP is invoked | llm_mcp_loop mcp_observation_from_energyplus | stage ok without twinpilot_mcp | code+runtime | **FAILED** |\n| Ollama responds | call_ollama_structured | 48 llm_structured_proposal provider=ollama | process :11434 | **VERIFIED** |\n| SafetyShield validates | validate_setpoint_action | matrix + unit tests | 10-safety | **VERIFIED** |\n| Unsafe action rejected | 35C demo | stage_log rejected reasons | runtime | **VERIFIED** |\n| LLM failure falls back | deterministic_fallback stage | 11-failure tmp_llm_ollama_down | 48 fallbacks | **VERIFIED** |\n| Dashboard uses real data | experiment_store→status | API matches raw summaries | 12-dashboard | **VERIFIED** |\n| No silent mock fallback | router building_status | energyplus missing→mock block | failure test | **FAILED** |\n| Results reproduce | run2 vs run1 | reproducibility-comparison.csv | diff 0 | **VERIFIED** |\n| Clean clone works | README scripts | clean-room-log exit 0 | gaps committed results | **PARTIALLY VERIFIED** |\n| Readiness 90/100 | prior report | independent score | rubric | **FAILED** |\n| Default DATA_MODE=energyplus | config.py / .env.example | API status data_mode | runtime | **VERIFIED** |\n| No ×1.12 multiplier | runtime comments only | API synthetic_multiplier_applied false | code+API | **VERIFIED** |\n| Baseline ~421.51 / agent ~416.00 / reductions | summaries | independent metrics | 05-fairness | **VERIFIED** |\n| HVAC/peak/comfort claims | summaries | independent | 05/08 | **VERIFIED** |\n| Agent actions 48/0/0 | action_counts | independent count | 07 | **VERIFIED** |\n| Baseline vs agent identical IDF/EPW/occ/period | fairness | hashes | 05 | **VERIFIED** |

## Counts

- VERIFIED: 20
- PARTIALLY VERIFIED: 1
- FAILED: 3
- NOT TESTED: 0


## Post-fix claim updates (2026-07-25T11:09:36.750049+00:00)

| Claim | Post-fix status | Evidence |
|-------|-------------------|----------|
| No silent mock fallback | **VERIFIED (after fix)** | `16-final-evidence/status-energyplus-missing-after-fix.json` |
| MCP is invoked | **PARTIALLY VERIFIED (after fix)** | in-process `call_tool`; not stdio MCP server |
| LLM failure falls back | **VERIFIED (counts fixed)** | `llm_fallback_recount` fallback=48 |


---

## Post MCP-transport remediation (`95a58e754e6a17ba987fa65d09401bd97f69ca43` · `2026-07-25T11:30:38.737937+00:00`)

Original Phase 9 FAILED/PARTIALLY rows above are historical. New evaluations:

| Claim | Status | Evidence |
|-------|--------|----------|
| Separate MCP server process | **VERIFIED** | client 51319 ≠ server 51324 |
| MCP initialization | **VERIFIED** | `initialize_ok` in mcp-runtime-trace.jsonl |
| tools/list | **VERIFIED** | tools_list event + 5 experiment tools |
| tools/call over stdio | **VERIFIED** | 240 request/response pairs |
| MCP request IDs recorded | **VERIFIED** | request_id on tools_call_* events |
| No direct handler in authoritative path | **VERIFIED** | llm_mcp_loop uses stdio_session only |
| MCP server failure detected | **VERIFIED** | failure matrix 8/8 |
| Safe fallback on MCP failure | **VERIFIED** | deterministic_fallback path |
| Fresh clone has no pre-generated results | **VERIFIED** | gitkeeps only; JSON count 0 |
| Dashboard honest no-data | **VERIFIED** | status-nodata.json |
| Fresh experiments populate dashboard | **VERIFIED** | status-with-results + checksums |
| Ollama prerequisite verified | **VERIFIED** | check_prerequisites.sh PASS |
| Full clean-clone workflow | **VERIFIED** | clean-room-stdio rerun exits 0 |

Independent readiness score after remediation: **95/100** (not copied from prior scores).
