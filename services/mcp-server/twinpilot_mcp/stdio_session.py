"""Stdio MCP client session for the EnergyPlus LLM experiment path.

Spawns ``python -m twinpilot_mcp`` as a **child process** and speaks MCP over stdio.
This is the proof that Eco-Loop uses a real MCP transport (separate PIDs), not an
in-process fake.

Does **not** import or call ``twinpilot_mcp.handlers.call_tool``.

Engineer map
------------
- ``StdioMcpSession.start`` — launch server, wait for initialize + tools/list
- ``list_tools`` / ``call_tool`` — JSON-RPC ops mirrored to the child
- ``_trace`` — append-only protocol evidence (initialize, tools/call, …)
- ``open_energyplus_mcp_session`` — convenience factory used by Path B/C scripts
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("twinpilot_mcp.stdio_session")

ROOT = Path(__file__).resolve().parents[3]  # repo root (services/mcp-server/twinpilot_mcp → ../..)
# __file__ = .../services/mcp-server/twinpilot_mcp/stdio_session.py
# parents[0]=twinpilot_mcp, [1]=mcp-server, [2]=services, [3]=repo root
MCP_SERVER_ROOT = Path(__file__).resolve().parents[1]


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class McpCallResult:
    ok: bool
    tool: str
    request_id: str
    result: dict[str, Any] | None = None
    error: str | None = None
    server_pid: int | None = None
    elapsed_s: float = 0.0
    raw_text: str | None = None


@dataclass
class StdioMcpSession:
    """Long-lived stdio MCP client talking to a separate server process.

    ``client_pid`` is this process; ``server_pid`` is the child. After ``start()``,
    judges should see ``client_pid != server_pid`` in hybrid/llm_mcp summaries.
    """

    trace_path: Path | None = None
    timeout_s: float = 15.0
    python_executable: str = field(default_factory=lambda: sys.executable)
    extra_env: dict[str, str] = field(default_factory=dict)
    client_pid: int = field(default_factory=os.getpid)
    server_pid: int | None = None
    initialized: bool = False
    tools: list[str] = field(default_factory=list)
    _jobs: queue.Queue = field(default_factory=queue.Queue, repr=False)
    _thread: threading.Thread | None = field(default=None, repr=False)
    _ready: threading.Event = field(default_factory=threading.Event, repr=False)
    _closed: threading.Event = field(default_factory=threading.Event, repr=False)
    _start_error: str | None = None
    _pidfile: Path | None = None
    _stderr_path: Path | None = None

    def _trace(self, event: str, **payload: Any) -> None:
        row = {"ts": _utc(), "event": event, "client_pid": self.client_pid, **payload}
        if self.server_pid is not None:
            row.setdefault("server_pid", self.server_pid)
        line = json.dumps(row, default=str)
        logger.info("mcp_trace %s", line)
        if self.trace_path is not None:
            self.trace_path.parent.mkdir(parents=True, exist_ok=True)
            with self.trace_path.open("a") as f:
                f.write(line + "\n")

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._closed.clear()
        self._ready.clear()
        self._start_error = None
        self._thread = threading.Thread(target=self._thread_main, name="mcp-stdio-client", daemon=True)
        self._thread.start()
        if not self._ready.wait(timeout=self.timeout_s + 5):
            raise TimeoutError(self._start_error or "MCP stdio session failed to become ready")
        if self._start_error:
            raise RuntimeError(self._start_error)

    def close(self) -> dict[str, Any]:
        self._jobs.put(None)
        if self._thread:
            self._thread.join(timeout=self.timeout_s + 5)
        self._closed.set()
        status = {
            "closed": True,
            "client_pid": self.client_pid,
            "server_pid": self.server_pid,
            "thread_alive": bool(self._thread and self._thread.is_alive()),
        }
        self._trace("session_closed", **status)
        return status

    def list_tools(self) -> list[str]:
        result = self._request({"op": "list_tools"})
        tools = result.get("tools") or []
        self.tools = list(tools)
        return self.tools

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> McpCallResult:
        request_id = str(uuid.uuid4())
        t0 = time.time()
        self._trace(
            "tools_call_request",
            request_id=request_id,
            tool=name,
            arguments=_sanitize(arguments or {}),
        )
        try:
            payload = self._request(
                {
                    "op": "call_tool",
                    "name": name,
                    "arguments": arguments or {},
                    "request_id": request_id,
                }
            )
            elapsed = time.time() - t0
            parsed = payload.get("result")
            server_pid = None
            if isinstance(parsed, dict):
                server_pid = parsed.get("server_pid")
                if server_pid is not None:
                    self.server_pid = int(server_pid)
            out = McpCallResult(
                ok=True,
                tool=name,
                request_id=request_id,
                result=parsed if isinstance(parsed, dict) else {"value": parsed},
                server_pid=self.server_pid,
                elapsed_s=elapsed,
                raw_text=payload.get("raw_text"),
            )
            self._trace(
                "tools_call_response",
                request_id=request_id,
                tool=name,
                ok=True,
                server_pid=self.server_pid,
                elapsed_s=elapsed,
                result=_sanitize(out.result or {}),
            )
            return out
        except Exception as exc:  # noqa: BLE001
            elapsed = time.time() - t0
            err = str(exc).strip() or f"{type(exc).__name__}: MCP tool call failed"
            out = McpCallResult(
                ok=False,
                tool=name,
                request_id=request_id,
                error=err,
                server_pid=self.server_pid,
                elapsed_s=elapsed,
            )
            self._trace(
                "tools_call_error",
                request_id=request_id,
                tool=name,
                ok=False,
                error=str(exc),
                elapsed_s=elapsed,
            )
            return out

    def _request(self, job: dict[str, Any]) -> dict[str, Any]:
        if self._closed.is_set() and not (self._thread and self._thread.is_alive()):
            raise RuntimeError("MCP session is closed")
        reply_q: queue.Queue = queue.Queue(maxsize=1)
        self._jobs.put((job, reply_q))
        try:
            kind, payload = reply_q.get(timeout=self.timeout_s + 5)
        except queue.Empty as exc:
            raise TimeoutError(f"MCP request timed out after {self.timeout_s}s") from exc
        if kind == "error":
            msg = str(payload).strip() or "MCP server request failed"
            raise RuntimeError(msg)
        return payload

    def _thread_main(self) -> None:
        try:
            asyncio.run(self._async_main())
        except Exception as exc:  # noqa: BLE001
            self._start_error = str(exc)
            self._trace("session_thread_error", error=str(exc))
            self._ready.set()

    async def _async_main(self) -> None:
        from mcp import ClientSession
        from mcp.client.stdio import StdioServerParameters, stdio_client

        evidence_dir = Path(
            os.environ.get("TWINPILOT_MCP_EVIDENCE_DIR", str(ROOT / "manual-verification" / "mcp-transport"))
        )
        evidence_dir.mkdir(parents=True, exist_ok=True)
        self._pidfile = evidence_dir / f"mcp-server-{os.getpid()}.pid"
        self._stderr_path = evidence_dir / "mcp-server-stderr.log"
        decision_log = evidence_dir / "mcp-server-decisions.jsonl"

        env = {
            **os.environ,
            "PYTHONPATH": os.pathsep.join(
                [
                    str(MCP_SERVER_ROOT),
                    str(ROOT / "services" / "simulator"),
                    str(ROOT / "services" / "optimizer"),
                    os.environ.get("PYTHONPATH", ""),
                ]
            ).strip(os.pathsep),
            "TWINPILOT_MCP_MODE": "energyplus_experiment",
            "TWINPILOT_MCP_TRANSPORT": "stdio",
            "TWINPILOT_MCP_PIDFILE": str(self._pidfile),
            "TWINPILOT_MCP_DECISION_LOG": str(decision_log),
            "TWINPILOT_MCP_LOG": os.environ.get("TWINPILOT_MCP_LOG", "INFO"),
            **self.extra_env,
        }

        params = StdioServerParameters(
            command=self.python_executable,
            args=["-m", "twinpilot_mcp"],
            env=env,
            cwd=str(ROOT),
        )

        err_f = self._stderr_path.open("a")
        self._trace(
            "server_spawn",
            command=params.command,
            args=params.args,
            mode="energyplus_experiment",
            pidfile=str(self._pidfile),
            stderr_log=str(self._stderr_path),
            start_ts=_utc(),
        )

        read_timeout = timedelta(seconds=self.timeout_s)
        async with stdio_client(params, errlog=err_f) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream, read_timeout_seconds=read_timeout) as session:
                init_result = await session.initialize()
                self.initialized = True
                # Read pidfile written by server
                for _ in range(50):
                    if self._pidfile.is_file():
                        try:
                            self.server_pid = int(self._pidfile.read_text().strip())
                            break
                        except ValueError:
                            pass
                    await asyncio.sleep(0.05)

                tools_result = await session.list_tools()
                self.tools = [t.name for t in tools_result.tools]
                self._trace(
                    "initialize_ok",
                    server_pid=self.server_pid,
                    protocol_version=getattr(init_result, "protocolVersion", None)
                    or getattr(init_result, "protocol_version", None),
                    server_info=str(getattr(init_result, "serverInfo", None) or getattr(init_result, "server_info", None)),
                    tools=self.tools,
                )
                self._trace("tools_list", tools=self.tools, server_pid=self.server_pid)
                self._ready.set()

                while True:
                    item = await asyncio.to_thread(self._jobs.get)
                    if item is None:
                        self._trace("shutdown_requested", server_pid=self.server_pid)
                        break
                    job, reply_q = item
                    try:
                        if job["op"] == "list_tools":
                            tools_result = await session.list_tools()
                            names = [t.name for t in tools_result.tools]
                            self.tools = names
                            reply_q.put(("ok", {"tools": names}))
                        elif job["op"] == "call_tool":
                            result = await session.call_tool(job["name"], job.get("arguments") or {})
                            text = _tool_result_text(result)
                            is_error = bool(getattr(result, "isError", False))
                            parsed: dict[str, Any] | Any
                            try:
                                parsed = json.loads(text) if text else {}
                            except json.JSONDecodeError:
                                parsed = {"raw": text}
                            # FastMCP often returns tool failures as text content without raising.
                            if not is_error and isinstance(parsed, dict) and "raw" in parsed:
                                raw = str(parsed.get("raw") or "")
                                if raw.startswith("Unknown tool:") or raw.startswith("Error executing tool"):
                                    is_error = True
                            if isinstance(parsed, dict) and parsed.get("server_pid") is not None:
                                self.server_pid = int(parsed["server_pid"])
                            if is_error:
                                reply_q.put(
                                    (
                                        "error",
                                        text or "MCP tool returned an error result",
                                    )
                                )
                            else:
                                reply_q.put(
                                    (
                                        "ok",
                                        {
                                            "result": parsed,
                                            "raw_text": text,
                                            "request_id": job.get("request_id"),
                                        },
                                    )
                                )
                        else:
                            reply_q.put(("error", f"unknown op {job.get('op')}"))
                    except Exception as exc:  # noqa: BLE001
                        err = str(exc).strip() or f"{type(exc).__name__}: MCP server call failed"
                        reply_q.put(("error", err))

        err_f.close()
        self._trace("server_process_exited", server_pid=self.server_pid)


def _tool_result_text(result: Any) -> str:
    content = getattr(result, "content", None) or []
    parts: list[str] = []
    for item in content:
        text = getattr(item, "text", None)
        if text is not None:
            parts.append(text)
        else:
            parts.append(str(item))
    return "\n".join(parts)


def _sanitize(obj: Any) -> Any:
    """Trim large payloads for evidence logs."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in {"advisor_prompt_hint"} and isinstance(v, str) and len(v) > 200:
                out[k] = v[:200] + "…"
            else:
                out[k] = _sanitize(v)
        return out
    if isinstance(obj, list):
        return [_sanitize(x) for x in obj[:50]]
    if isinstance(obj, str) and len(obj) > 800:
        return obj[:800] + "…"
    return obj


def open_energyplus_mcp_session(
    *,
    trace_path: Path | None = None,
    timeout_s: float = 15.0,
) -> StdioMcpSession:
    session = StdioMcpSession(trace_path=trace_path, timeout_s=timeout_s)
    session.start()
    return session
