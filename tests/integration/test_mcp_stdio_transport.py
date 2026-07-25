"""Prove MCP stdio transport uses a separate OS process (not in-process handlers)."""

from __future__ import annotations

import json
import os
import signal
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def mcp_paths_on_syspath():
    import sys

    paths = [
        str(ROOT / "services" / "mcp-server"),
        str(ROOT / "services" / "simulator"),
        str(ROOT / "services" / "optimizer"),
    ]
    for p in paths:
        if p not in sys.path:
            sys.path.insert(0, p)
    return paths


def test_stdio_mcp_server_pid_differs_from_client(mcp_paths_on_syspath, tmp_path):
    from twinpilot_mcp.stdio_session import open_energyplus_mcp_session

    os.environ["TWINPILOT_MCP_EVIDENCE_DIR"] = str(tmp_path)
    trace = tmp_path / "trace.jsonl"
    session = open_energyplus_mcp_session(trace_path=trace, timeout_s=20)
    try:
        assert session.initialized is True
        assert session.server_pid is not None
        assert session.server_pid != session.client_pid
        tools = session.list_tools()
        assert "get_building_observation" in tools
        assert "validate_control_action" in tools
        obs = {
            "outdoor_c": 30.0,
            "zone_temps_c": {"SPACE1-1": 24.0},
            "occupancy": {"SPACE1-1": 1.0},
            "cooling_setpoint_c": 24.0,
        }
        result = session.call_tool(
            "get_building_observation", {"observation_json": json.dumps(obs)}
        )
        assert result.ok is True
        assert result.server_pid == session.server_pid
        assert result.server_pid != session.client_pid
        # Evidence must not look like in-process handler dispatch.
        text = trace.read_text()
        assert "initialize_ok" in text
        assert "tools_list" in text
        assert "tools_call_request" in text
        assert "tools_call_response" in text
        assert "handlers.call_tool" not in text
    finally:
        session.close()


def test_killing_mcp_server_fails_client_call(mcp_paths_on_syspath, tmp_path):
    from twinpilot_mcp.stdio_session import open_energyplus_mcp_session

    os.environ["TWINPILOT_MCP_EVIDENCE_DIR"] = str(tmp_path)
    session = open_energyplus_mcp_session(trace_path=tmp_path / "trace.jsonl", timeout_s=10)
    try:
        assert session.server_pid is not None
        os.kill(session.server_pid, signal.SIGKILL)
        # Wait briefly for the process to disappear.
        time.sleep(0.2)
        result = session.call_tool("get_controller_constraints", {})
        assert result.ok is False
        assert result.error is not None
        assert str(result.error).strip() != "" or result.request_id
        # Stronger: a successful MCP invocation must never be reported after kill.
        assert result.ok is False
    finally:
        try:
            session.close()
        except Exception:
            pass


def test_authoritative_llm_script_does_not_import_handlers_call_tool():
    src = (ROOT / "scripts" / "llm_mcp_loop.py").read_text()
    assert "from twinpilot_mcp.handlers import call_tool" not in src
    assert "handlers import call_tool" not in src
    assert "open_energyplus_mcp_session" in src
    assert "stdio" in src.lower()
