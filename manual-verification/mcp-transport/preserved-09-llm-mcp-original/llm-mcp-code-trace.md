# LLM/MCP Code Trace (Phase 9)

Report: `2026-07-25T11:08:07.584946+00:00`

## Intended claim

EnergyPlus → MCP → Ollama → schema → SafetyShield → actuator

## Actual code path (`scripts/llm_mcp_loop.py`)

| Stage | Implementation | Classification |
|-------|----------------|----------------|
| EnergyPlus observation | `run_experiment` callback obs | **real** |
| MCP resource/tool | `mcp_observation_from_energyplus()` — docstring: "Simulate MCP resource/tool payload"; does **not** import/start `twinpilot_mcp` | **mocked / simulated packaging** |
| Ollama | `urllib` POST to `$OLLAMA_BASE_URL/api/generate` | **real HTTP client** |
| Parse/schema | `json.loads` on model response | **real** (lightweight) |
| SafetyShield | `validate_setpoint_action` | **real** |
| Actuator | same `set_actuator_value(Clg-SetP-Sch)` | **real** when approved |
| Fallback | on Ollama exception → `propose_agent_cooling_setpoint` | **real** |

Separate real MCP server exists at `services/mcp-server/twinpilot_mcp/` but is **not wired** into this experiment script.

## Fixed responses search

No hardcoded successful Ollama JSON fixtures in `llm_mcp_loop.py`. Unsafe 35°C demo is intentionally injected post-run for SafetyShield proof.
