# Recovery After Failure

Generated: 2026-07-25T11:52:00Z

## Sequence
1. Normal LLM+MCP path completed successfully (client_pid=65999, server_pid=66004, 48 Ollama proposals).
2. Ollama unavailable test used `OLLAMA_BASE_URL=http://127.0.0.1:1` → 48 proposal failures → 48 deterministic_fallback actions (see `ollama-fallback.log`).
3. Recovery probe restored local Ollama health and opened a fresh stdio MCP session.

## Evidence
- Fallback: `final-release/evidence/ollama-fallback.log`
- Recovery log: `final-release/logs/recovery-after-failure.log`
- Recovery MCP trace: `final-release/evidence/recovery-mcp-trace.jsonl`

## Result
See log for PID proof and Ollama response.
PASS

