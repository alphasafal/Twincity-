# TwinPilot MCP Server

Model Context Protocol (MCP) server that exposes TwinPilot building context and **narrowly scoped** control tools. All mutating actions go through the TwinPilot REST API and Safety Shield. There is **no** `set_any_actuator` tool.

## Requirements

- Python 3.11+
- TwinPilot API running (default `http://localhost:8000`)
- Dependencies: `mcp`, `httpx`, `pydantic`

## Install

From the repo root or this directory:

```bash
cd services/mcp-server
pip install -e .
```

Or with uv:

```bash
cd services/mcp-server
uv pip install -e .
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `TWINPILOT_API_URL` | `http://localhost:8000` | TwinPilot REST base URL |
| `TWINPILOT_API_EMAIL` | `manager@twinpilot.demo` | Demo / service login email |
| `TWINPILOT_API_PASSWORD` | `TwinPilot-Manager-Demo!` | Demo / service login password |
| `TWINPILOT_API_TOKEN` | _(empty)_ | Optional pre-issued bearer token |
| `TWINPILOT_BUILDING_ID` | _(auto)_ | Pin a building; otherwise first building is used |
| `TWINPILOT_MCP_TRANSPORT` | `stdio` | FastMCP transport (`stdio`, or SDK-supported HTTP) |
| `TWINPILOT_MCP_FORCE_FALLBACK` | `0` | Force stdio JSON-RPC fallback server |

## Run

```bash
# Preferred entrypoint
python -m twinpilot_mcp

# Or via console script after install
twinpilot-mcp

# Inspect advertised tools/resources without a host
python -m twinpilot_mcp --catalog

# Force fallback JSON-RPC stdio server
python -m twinpilot_mcp --fallback
```

The server prefers the official `mcp` FastMCP API, then the low-level `mcp.server.Server`, then a built-in stdio JSON-RPC fallback that still lists and dispatches the same catalog.

## MCP host config example

```json
{
  "mcpServers": {
    "twinpilot": {
      "command": "python",
      "args": ["-m", "twinpilot_mcp"],
      "env": {
        "TWINPILOT_API_URL": "http://localhost:8000",
        "TWINPILOT_API_EMAIL": "manager@twinpilot.demo",
        "TWINPILOT_API_PASSWORD": "TwinPilot-Manager-Demo!"
      }
    }
  }
}
```

Ensure `PYTHONPATH` includes this package (or install it editable) so `python -m twinpilot_mcp` resolves.

## Safety rules (summary)

- Resources are read-only.
- `apply_validated_plan` **requires** `validation_token` from `validate_plan`.
- `request_zone_setpoint` **requires** `zone_id`, `temperature`, `duration`, `reason`.
- Unrestricted actuation (`set_any_actuator`) is never registered.

See [`docs/MCP.md`](../../docs/MCP.md) for the full resource/tool reference.
