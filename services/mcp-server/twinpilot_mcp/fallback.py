"""Minimal stdio JSON-RPC MCP server fallback.

Used when the official `mcp` package is unavailable or its FastMCP API
differs across versions. Still advertises the full TwinPilot tool/resource
catalog and dispatches through the shared handlers.
"""

from __future__ import annotations

import json
import sys
import traceback
from typing import Any, TextIO

from twinpilot_mcp import __version__
from twinpilot_mcp.catalog import RESOURCES, TOOLS
from twinpilot_mcp.client import TwinPilotClient
from twinpilot_mcp.handlers import call_tool, read_resource

PROTOCOL_VERSION = "2024-11-05"


class StdioJsonRpcServer:
    """Very small MCP-compatible server over newline-delimited JSON-RPC 2.0."""

    def __init__(
        self,
        client: TwinPilotClient | None = None,
        *,
        stdin: TextIO[str] | None = None,
        stdout: TextIO[str] | None = None,
    ) -> None:
        self.client = client or TwinPilotClient()
        self.stdin = stdin or sys.stdin
        self.stdout = stdout or sys.stdout
        self._initialized = False

    def _write(self, message: dict[str, Any]) -> None:
        self.stdout.write(json.dumps(message, default=str) + "\n")
        self.stdout.flush()

    def _result(self, req_id: Any, result: Any) -> None:
        self._write({"jsonrpc": "2.0", "id": req_id, "result": result})

    def _error(self, req_id: Any, code: int, message: str, data: Any = None) -> None:
        err: dict[str, Any] = {"code": code, "message": message}
        if data is not None:
            err["data"] = data
        self._write({"jsonrpc": "2.0", "id": req_id, "error": err})

    def handle(self, message: dict[str, Any]) -> None:
        method = message.get("method")
        req_id = message.get("id")
        params = message.get("params") or {}

        try:
            if method == "initialize":
                self._initialized = True
                self._result(
                    req_id,
                    {
                        "protocolVersion": PROTOCOL_VERSION,
                        "capabilities": {
                            "resources": {"listChanged": False},
                            "tools": {"listChanged": False},
                        },
                        "serverInfo": {
                            "name": "twinpilot-mcp",
                            "version": __version__,
                        },
                        "instructions": (
                            "TwinPilot MCP exposes read-only building resources and narrowly "
                            "scoped control tools. Never use set_any_actuator. "
                            "apply_validated_plan requires a validation_token from validate_plan. "
                            "request_zone_setpoint requires zone_id, temperature, duration, reason."
                        ),
                    },
                )
                return

            if method == "notifications/initialized":
                return

            if method == "ping":
                self._result(req_id, {})
                return

            if method == "resources/list":
                self._result(req_id, {"resources": RESOURCES})
                return

            if method == "resources/read":
                uri = params.get("uri")
                if not uri:
                    self._error(req_id, -32602, "Missing uri")
                    return
                text = read_resource(self.client, uri)
                self._result(
                    req_id,
                    {
                        "contents": [
                            {
                                "uri": uri,
                                "mimeType": "application/json",
                                "text": text,
                            }
                        ]
                    },
                )
                return

            if method == "tools/list":
                self._result(req_id, {"tools": TOOLS})
                return

            if method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments") or {}
                if not name:
                    self._error(req_id, -32602, "Missing tool name")
                    return
                text = call_tool(self.client, name, arguments)
                self._result(
                    req_id,
                    {
                        "content": [{"type": "text", "text": text}],
                        "isError": False,
                    },
                )
                return

            if req_id is not None:
                self._error(req_id, -32601, f"Method not found: {method}")
        except Exception as exc:  # noqa: BLE001 — surface tool/API failures to client
            if req_id is not None:
                self._error(
                    req_id,
                    -32000,
                    str(exc),
                    data={"traceback": traceback.format_exc()},
                )

    def run(self) -> None:
        for line in self.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                self._error(None, -32700, f"Parse error: {exc}")
                continue
            self.handle(message)


def run_fallback() -> None:
    with TwinPilotClient() as client:
        StdioJsonRpcServer(client).run()
