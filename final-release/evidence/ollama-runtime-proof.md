# Ollama Runtime Proof

Generated: 2026-07-25T11:51:44.057187+00:00

## Configuration

- Local Ollama prerequisite (not cloud)
- Model: `llama3.2:1b` (default in run_llm_mcp_experiment.sh)
- Endpoint pattern: `{OLLAMA_BASE_URL}/api/generate` with `format=json`

## Runtime

- Successful structured proposals logged: 48
- Failed proposal attempts in this run: 0
- Sample proposal: `{"proposed_cooling_setpoint_c": 22, "reason": "Maintaining comfort within a reasonable range to minimize energy consumption.", "confidence": 0.9}`
- Schema validation: proposal must include `proposed_cooling_setpoint_c`; confidence clamped 0–1
- SafetyShield: every proposal passes `validate_setpoint_action` before actuator write
- Evidence file: `ollama-structured-responses.jsonl` (48 rows)

## Verdict

**PASS**
