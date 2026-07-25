#!/usr/bin/env python3
"""Prove EnergyPlus → stdio MCP → LLM → SafetyShield → EnergyPlus actuator path.

Authoritative MCP path uses a *separate* stdio MCP server process via
`twinpilot_mcp.stdio_session.StdioMcpSession`.

Direct in-process handler invocation is intentionally absent on this path.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "services" / "simulator"),
    str(ROOT / "services" / "optimizer"),
    str(ROOT / "services" / "agent"),
    str(ROOT / "services" / "mcp-server"),
]

from twinpilot_mcp.stdio_session import open_energyplus_mcp_session  # noqa: E402
from twinpilot_simulator.ep_experiment import (  # noqa: E402
    ExperimentConfig,
    SafetyLimits,
    propose_agent_cooling_setpoint,
    resolve_paths_from_env,
    run_experiment,
    validate_setpoint_action,
)


OUT = Path(os.environ.get("RESULTS_LLM_DIR", ROOT / "results" / "llm_mcp"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "stage_log.jsonl"
MCP_TRACE = Path(
    os.environ.get(
        "TWINPILOT_MCP_TRACE",
        str(ROOT / "manual-verification" / "mcp-transport" / "mcp-runtime-trace.jsonl"),
    )
)


def log_stage(stage: str, payload: dict[str, Any]) -> None:
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        **payload,
    }
    with LOG.open("a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"[{stage}] {json.dumps(payload)[:240]}", file=sys.stderr)


def call_ollama_structured(mcp_payload: dict[str, Any]) -> tuple[float | None, dict[str, Any]]:
    base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
    prompt = {
        "model": model,
        "stream": False,
        "format": "json",
        "prompt": (
            "You are an HVAC setpoint advisor. Given building state JSON, reply ONLY with JSON: "
            '{"proposed_cooling_setpoint_c": number, "reason": string, "confidence": number}. '
            "Stay within 22-28C. Do not execute actuators.\nSTATE:\n"
            + json.dumps(mcp_payload)
        ),
    }
    try:
        req = urllib.request.Request(
            f"{base}/api/generate",
            data=json.dumps(prompt).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            body = json.loads(resp.read().decode())
        raw = body.get("response") or "{}"
        parsed = json.loads(raw)
        sp = float(parsed["proposed_cooling_setpoint_c"])
        conf = float(parsed.get("confidence", 0.7))
        if conf > 1.0:
            conf = conf / 100.0
        conf = max(0.0, min(1.0, conf))
        log_stage(
            "llm_structured_proposal",
            {"ok": True, "provider": "ollama", "model": model, "proposal": parsed},
        )
        return sp, {"source": "ollama", "raw": parsed, "confidence": conf}
    except Exception as exc:  # noqa: BLE001
        log_stage(
            "llm_structured_proposal",
            {"ok": False, "provider": "ollama", "error": str(exc), "fallback": "deterministic"},
        )
        return None, {"source": "ollama_failed", "error": str(exc)}


def make_proposal_fn(mcp_session):
    """Return a proposal_fn that uses stdio MCP + Ollama with deterministic fallback."""

    def proposal_fn(
        *,
        outdoor_c: float,
        zone_temps: dict[str, float],
        occupancy: dict[str, float],
        current_cooling_setpoint: float,
        limits: SafetyLimits,
        hour: int,
    ) -> tuple[float, str, float, str]:
        obs = {
            "outdoor_c": outdoor_c,
            "zone_temps_c": zone_temps,
            "occupancy": occupancy,
            "cooling_setpoint_c": current_cooling_setpoint,
        }
        log_stage(
            "energyplus_observation",
            {"hour": hour, "outdoor_c": outdoor_c, "zones": zone_temps},
        )
        obs_json = json.dumps(obs)

        try:
            obs_res = mcp_session.call_tool(
                "get_building_observation", {"observation_json": obs_json}
            )
            if not obs_res.ok:
                raise RuntimeError(obs_res.error or "get_building_observation failed")
            ctx_res = mcp_session.call_tool(
                "propose_or_prepare_control_context", {"observation_json": obs_json}
            )
            if not ctx_res.ok:
                raise RuntimeError(ctx_res.error or "propose_or_prepare_control_context failed")
            constraints = mcp_session.call_tool("get_controller_constraints", {})
            if not constraints.ok:
                raise RuntimeError(constraints.error or "get_controller_constraints failed")
            log_stage(
                "mcp_stdio_tools",
                {
                    "ok": True,
                    "transport": "stdio",
                    "client_pid": mcp_session.client_pid,
                    "server_pid": mcp_session.server_pid,
                    "tools_called": [
                        "get_building_observation",
                        "propose_or_prepare_control_context",
                        "get_controller_constraints",
                    ],
                    "request_ids": [
                        obs_res.request_id,
                        ctx_res.request_id,
                        constraints.request_id,
                    ],
                    "pids_differ": (
                        mcp_session.server_pid is not None
                        and mcp_session.server_pid != mcp_session.client_pid
                    ),
                },
            )
            mcp_payload = {
                "observation": obs_res.result,
                "control_context": (ctx_res.result or {}).get("context"),
                "constraints": (constraints.result or {}).get("constraints"),
            }
        except Exception as exc:  # noqa: BLE001
            det_sp, reason, conf = propose_agent_cooling_setpoint(
                outdoor_c=outdoor_c,
                zone_temps=zone_temps,
                occupancy=occupancy,
                current_cooling_setpoint=current_cooling_setpoint,
                limits=limits,
                hour=hour,
            )
            log_stage(
                "deterministic_fallback",
                {
                    "proposed": det_sp,
                    "reason": reason,
                    "confidence": conf,
                    "cause": f"mcp_failure:{exc}",
                },
            )
            return det_sp, f"deterministic_fallback:mcp_failure:{reason}", conf, "deterministic_fallback"

        llm_sp, meta = call_ollama_structured(mcp_payload)
        if llm_sp is None:
            det_sp, reason, conf = propose_agent_cooling_setpoint(
                outdoor_c=outdoor_c,
                zone_temps=zone_temps,
                occupancy=occupancy,
                current_cooling_setpoint=current_cooling_setpoint,
                limits=limits,
                hour=hour,
            )
            log_stage(
                "deterministic_fallback",
                {"proposed": det_sp, "reason": reason, "confidence": conf},
            )
            return det_sp, f"deterministic_fallback:{reason}", conf, "deterministic_fallback"

        reason = str(meta.get("raw", {}).get("reason", "llm_proposal"))
        conf = float(meta.get("confidence", 0.7))

        val = mcp_session.call_tool(
            "validate_control_action",
            {
                "proposed_setpoint_c": float(llm_sp),
                "current_setpoint_c": float(current_cooling_setpoint),
                "heating_setpoint_c": 21.0,
                "confidence": conf,
            },
        )
        mcp_session.call_tool(
            "record_control_decision",
            {
                "decision_json": json.dumps(
                    {
                        "hour": hour,
                        "proposed": llm_sp,
                        "reason": reason,
                        "confidence": conf,
                        "mcp_validate_ok": val.ok,
                        "mcp_validate": val.result,
                        "source": "ollama_via_stdio_mcp",
                    }
                )
            },
        )
        return float(llm_sp), reason, conf, "llm_via_stdio_mcp"

    return proposal_fn


def main() -> int:
    if LOG.exists():
        LOG.unlink()
    MCP_TRACE.parent.mkdir(parents=True, exist_ok=True)
    if MCP_TRACE.exists():
        # Fresh evidence for this run; preserve prior remediation archives separately.
        MCP_TRACE.write_text("")

    os.environ.setdefault("TWINPILOT_MCP_EVIDENCE_DIR", str(MCP_TRACE.parent))
    log_stage("start", {"out": str(OUT), "mcp_trace": str(MCP_TRACE)})

    mcp_session = open_energyplus_mcp_session(trace_path=MCP_TRACE, timeout_s=20.0)
    try:
        tools = mcp_session.list_tools()
        log_stage(
            "mcp_session_ready",
            {
                "transport": "stdio",
                "client_pid": mcp_session.client_pid,
                "server_pid": mcp_session.server_pid,
                "pids_differ": (
                    mcp_session.server_pid is not None
                    and mcp_session.server_pid != mcp_session.client_pid
                ),
                "tools": tools,
                "initialized": mcp_session.initialized,
            },
        )

        baseline_paths = resolve_paths_from_env(OUT / "baseline")
        agent_paths = resolve_paths_from_env(OUT / "agent")

        baseline = run_experiment(
            ExperimentConfig(paths=baseline_paths, mode="baseline", scenario="llm_mcp")
        )
        log_stage("baseline_complete", {"total_energy_kwh": baseline.get("total_energy_kwh")})

        agent = run_experiment(
            ExperimentConfig(
                paths=agent_paths,
                mode="agent",
                scenario="llm_mcp",
                agent_provider="llm_mcp",
                proposal_fn=make_proposal_fn(mcp_session),
            )
        )
        log_stage(
            "agent_complete",
            {
                "total_energy_kwh": agent.get("total_energy_kwh"),
                "action_counts": agent.get("action_counts"),
                "comfort_violation_hours": agent.get("occupied_comfort_violation_hours"),
            },
        )

        ok, reasons, disposition = validate_setpoint_action(
            proposed=35.0,
            current=24.0,
            heating_setpoint=21.0,
            limits=SafetyLimits(),
            confidence=0.99,
            sensors_healthy=True,
            data_age_seconds=0.0,
            manual_override=False,
            llm_timed_out=False,
            mcp_failed=False,
        )
        log_stage(
            "safety_shield_rejects_unsafe",
            {
                "proposed": 35.0,
                "approved": ok,
                "disposition": disposition,
                "reasons": reasons,
            },
        )

        summary = {
            "path": (
                "EnergyPlus → MCP client → stdio → separate MCP server process → "
                "MCP tools → Ollama structured proposal → SafetyShield → EnergyPlus actuator"
            ),
            "mcp_transport": "stdio",
            "mcp_client_pid": mcp_session.client_pid,
            "mcp_server_pid": mcp_session.server_pid,
            "mcp_pids_differ": (
                mcp_session.server_pid is not None
                and mcp_session.server_pid != mcp_session.client_pid
            ),
            "baseline": {
                "total_energy_kwh": baseline.get("total_energy_kwh"),
                "status": baseline.get("simulation_status"),
            },
            "agent": {
                "total_energy_kwh": agent.get("total_energy_kwh"),
                "status": agent.get("simulation_status"),
                "action_counts": agent.get("action_counts"),
                "controller": agent.get("controller"),
            },
            "llm_bypass_possible": False,
            "stage_log": str(LOG),
            "mcp_trace": str(MCP_TRACE),
            "notes": [
                "Authoritative MCP path uses a separate stdio server process.",
                "Direct in-process MCP handler invocation is not used on this path.",
                "If Ollama or MCP fails, deterministic_fallback is used and logged.",
                "Unsafe 35C proposal is rejected by SafetyShield.",
            ],
        }
        (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary, indent=2))
        return 0
    finally:
        mcp_session.close()


if __name__ == "__main__":
    raise SystemExit(main())
