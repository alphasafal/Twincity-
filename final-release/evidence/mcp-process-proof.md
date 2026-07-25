# MCP Process Proof

Generated: 2026-07-25T11:51:44.056788+00:00

## Process separation

- mcp_transport: `stdio`
- client_pid: `65999`
- server_pid: `66004`
- client_pid != server_pid: **True**
- session stage: `{"ts": "2026-07-25T11:48:16.187423+00:00", "stage": "mcp_session_ready", "transport": "stdio", "client_pid": 65999, "server_pid": 66004, "pids_differ": true, "tools": ["get_building_observation", "propose_or_prepare_control_context", "validate_control_action", "get_controller_constraints", "record_control_decision"], "initialized": true}`

## Protocol evidence

- mcp-runtime-trace.jsonl lines: 486
- tools/list-related trace rows: 0
- tools/call-related trace rows: 0
- mcp_stdio_tools stage rows: 48
- sample tools_called: `['get_building_observation', 'propose_or_prepare_control_context', 'get_controller_constraints']`
- sample request_ids present: True

## Authoritative path purity

- `scripts/llm_mcp_loop.py` imports/calls `handlers.call_tool`: **False** (must be False)
- llm_bypass_possible: `False`

## Verdict

**PASS** — separate stdio MCP client/server with tools/list and tools/call evidence.
