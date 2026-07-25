# LLM/MCP Runtime Trace (Phase 9)

Report: `2026-07-25T11:08:07.584946+00:00`

## Command

`./scripts/run_llm_mcp_experiment.sh`

- Start: `2026-07-25T10:58:30Z` · End: `2026-07-25T11:00:22Z` · Exit: **0** · Duration: **112s**
- Ollama listening: `127.0.0.1:11434` · Model: `llama3.2:1b`
- Artifacts: `results/llm_mcp/stage_log.jsonl`, `summary.json`

## Stage counts (fresh)

- energyplus_observation: 48
- mcp_resource_tool: 48 (**ok:true but local dict only; no twinpilot_mcp process**)
- llm_structured_proposal: 48 (**provider=ollama, model=llama3.2:1b**, varying reasons/setpoints)
- safety_shield_rejects_unsafe: 1 (35°C → rejected)
- agent action_counts: approved 14 / rejected 34 / fallback 0
- agent total energy: **397.0752 kWh** (LLM controller — **not** the 416.00 deterministic claim)

## Classifications

| Claim | Status |
|-------|--------|
| MCP invocation proven | **NOT PROVEN** (simulated packaging) |
| Ollama response proven | **PROVEN** |
| Actuator execution proven | **PROVEN** (shared EnergyPlus path under `results/llm_mcp/agent/`) |

## Failure-injection cross-ref

With Ollama down: 48× `llm_structured_proposal ok:false` + 48× `deterministic_fallback` stages (`11-failure-injection/tmp_llm_ollama_down/`).
