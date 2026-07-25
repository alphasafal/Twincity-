# MCP Process Proof (stdio)

Pre-remediation commit: `b63311c3f929a8d9a85dfbf8ed5845231c486b6b`  
Original in-process finding preserved under `preserved-09-llm-mcp-original/` and Phase 9 reports (do not rewrite).

## Runtime evidence (fresh)

Command: `./scripts/run_llm_mcp_experiment.sh`

From `results/llm_mcp/summary.json`:

- `mcp_transport`: **stdio**
- `mcp_client_pid`: **38195**
- `mcp_server_pid`: **38200**
- `mcp_pids_differ`: **true**

From `mcp-runtime-trace.jsonl` event counts:

| Event | Count |
|-------|------:|
| server_spawn | 1 |
| initialize_ok | 1 |
| tools_list | 1 |
| tools_call_request | 240 |
| tools_call_response | 240 |
| session_closed | 1 |

Stage log contains `mcp_stdio_tools` × 48 with `transport=stdio` and `pids_differ=true`.

## Automated test

`tests/integration/test_mcp_stdio_transport.py` asserts `server_pid != client_pid` and that killing the server makes subsequent client calls fail (`ok=False`).

## Authoritative path

`scripts/llm_mcp_loop.py` uses `open_energyplus_mcp_session` / stdio only. It does not import `twinpilot_mcp.handlers.call_tool`.
