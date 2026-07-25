"""Stdio MCP server for EnergyPlus closed-loop experiment observations.

Runs as a *separate process*. Tools accept EnergyPlus Runtime observations as
JSON arguments (the co-simulation loop owns live state; this server does not
call the TwinPilot HTTP API).

All diagnostic logging goes to stderr — stdout is reserved for MCP JSON-RPC.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("twinpilot_mcp.energyplus_experiment")

# Optional path for append-only decision records (set by client).
_DECISION_LOG = Path(os.environ.get("TWINPILOT_MCP_DECISION_LOG", "") or "")
_DECISIONS: list[dict[str, Any]] = []


def _configure_stderr_logging() -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
    root.setLevel(os.getenv("TWINPILOT_MCP_LOG", "INFO").upper())


def _pid_payload() -> dict[str, Any]:
    return {
        "server_pid": os.getpid(),
        "server_mode": "energyplus_experiment",
        "transport": "stdio",
        "ts": datetime.now(timezone.utc).isoformat(),
    }


def _parse_observation(observation_json: str) -> dict[str, Any]:
    if not isinstance(observation_json, str) or not observation_json.strip():
        raise ValueError("observation_json must be a non-empty JSON string")
    data = json.loads(observation_json)
    if not isinstance(data, dict):
        raise ValueError("observation_json must decode to an object")
    required = ("outdoor_c", "zone_temps_c", "occupancy", "cooling_setpoint_c")
    missing = [k for k in required if k not in data]
    if missing:
        raise ValueError(f"observation missing keys: {missing}")
    if not isinstance(data["zone_temps_c"], dict):
        raise ValueError("zone_temps_c must be an object")
    return data


def _constraints() -> dict[str, Any]:
    # Keep aligned with ep_experiment.SafetyLimits defaults without importing
    # heavy EnergyPlus bindings into the MCP child if avoidable.
    return {
        "min_cooling_setpoint_c": 22.0,
        "max_cooling_setpoint_c": 28.0,
        "max_setpoint_change_per_interval_c": 1.0,
        "heating_cooling_deadband_c": 1.5,
        "comfort_occupied_min_c": 21.0,
        "comfort_occupied_max_c": 26.0,
        "max_data_age_seconds": 900.0,
        "notes": "Authoritative actuation still gated by SafetyShield in the EnergyPlus loop.",
    }


def build_energyplus_experiment_fastmcp():
    """Build FastMCP app exposing EnergyPlus experiment tools over stdio."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "TwinPilot-EnergyPlus-Experiment",
        instructions=(
            "EnergyPlus experiment MCP tools. Observations are supplied by the "
            "client from the EnergyPlus Runtime API. This server never writes "
            "actuators. Stdout is MCP protocol only."
        ),
    )

    @mcp.tool()
    def get_building_observation(observation_json: str) -> str:
        """Normalize and return an EnergyPlus Runtime observation payload."""
        obs = _parse_observation(observation_json)
        out = {
            **_pid_payload(),
            "tool": "get_building_observation",
            "resource": "building://energyplus-observation",
            "outdoor_temperature_c": obs["outdoor_c"],
            "zones": {
                z: {
                    "temperature_c": t,
                    "occupancy": (obs.get("occupancy") or {}).get(z),
                }
                for z, t in obs["zone_temps_c"].items()
            },
            "cooling_setpoint_c": obs["cooling_setpoint_c"],
            "source": "energyplus_runtime_observation",
        }
        logger.info("tool=get_building_observation server_pid=%s", os.getpid())
        return json.dumps(out)

    @mcp.tool()
    def propose_or_prepare_control_context(observation_json: str) -> str:
        """Prepare structured control context for an LLM proposal step."""
        obs = _parse_observation(observation_json)
        zones = obs["zone_temps_c"]
        occ = obs.get("occupancy") or {}
        avg_temp = sum(float(v) for v in zones.values()) / max(1, len(zones))
        total_occ = sum(float(v or 0) for v in occ.values())
        ctx = {
            **_pid_payload(),
            "tool": "propose_or_prepare_control_context",
            "context": {
                "outdoor_temperature_c": obs["outdoor_c"],
                "average_zone_temperature_c": avg_temp,
                "total_occupancy": total_occ,
                "current_cooling_setpoint_c": obs["cooling_setpoint_c"],
                "zones": {
                    z: {"temperature_c": t, "occupancy": occ.get(z)}
                    for z, t in zones.items()
                },
                "constraints": _constraints(),
                "advisor_prompt_hint": (
                    "Reply ONLY with JSON: "
                    '{"proposed_cooling_setpoint_c": number, "reason": string, "confidence": number}. '
                    "Stay within 22-28C. Do not execute actuators."
                ),
            },
        }
        logger.info("tool=propose_or_prepare_control_context server_pid=%s", os.getpid())
        return json.dumps(ctx)

    @mcp.tool()
    def validate_control_action(
        proposed_setpoint_c: float,
        current_setpoint_c: float,
        heating_setpoint_c: float = 21.0,
        confidence: float = 0.9,
    ) -> str:
        """Run SafetyShield-equivalent checks (non-actuating advisory result)."""
        # Import lazily so the MCP process can start even if simulator path is unset.
        root = Path(__file__).resolve().parents[2]  # services/
        sim = root / "simulator"
        if str(sim) not in sys.path:
            sys.path.insert(0, str(sim))
        from twinpilot_simulator.ep_experiment import SafetyLimits, validate_setpoint_action

        limits = SafetyLimits()
        ok, reasons, disposition = validate_setpoint_action(
            proposed=float(proposed_setpoint_c),
            current=float(current_setpoint_c),
            heating_setpoint=float(heating_setpoint_c),
            limits=limits,
            confidence=float(confidence),
            sensors_healthy=True,
            data_age_seconds=0.0,
            manual_override=False,
            llm_timed_out=False,
            mcp_failed=False,
        )
        out = {
            **_pid_payload(),
            "tool": "validate_control_action",
            "approved": ok,
            "disposition": disposition,
            "reasons": reasons,
            "proposed_setpoint_c": proposed_setpoint_c,
            "current_setpoint_c": current_setpoint_c,
            "note": "Advisory MCP validation; EnergyPlus loop still applies authoritative SafetyShield.",
        }
        logger.info(
            "tool=validate_control_action approved=%s disposition=%s server_pid=%s",
            ok,
            disposition,
            os.getpid(),
        )
        return json.dumps(out)

    @mcp.tool()
    def get_controller_constraints() -> str:
        """Return cooling-setpoint controller constraints."""
        out = {**_pid_payload(), "tool": "get_controller_constraints", "constraints": _constraints()}
        logger.info("tool=get_controller_constraints server_pid=%s", os.getpid())
        return json.dumps(out)

    @mcp.tool()
    def record_control_decision(decision_json: str) -> str:
        """Record a control decision for audit (server-side log; no actuation)."""
        if not isinstance(decision_json, str) or not decision_json.strip():
            raise ValueError("decision_json must be a non-empty JSON string")
        decision = json.loads(decision_json)
        if not isinstance(decision, dict):
            raise ValueError("decision_json must decode to an object")
        row = {**_pid_payload(), "tool": "record_control_decision", "decision": decision}
        _DECISIONS.append(row)
        if _DECISION_LOG:
            _DECISION_LOG.parent.mkdir(parents=True, exist_ok=True)
            with _DECISION_LOG.open("a") as f:
                f.write(json.dumps(row) + "\n")
        logger.info("tool=record_control_decision n=%s server_pid=%s", len(_DECISIONS), os.getpid())
        return json.dumps({"ok": True, "recorded": len(_DECISIONS), **_pid_payload()})

    @mcp.tool()
    def select_energy_conservation_measure(strategy_json: str) -> str:
        """Record/validate a supervisory energy-conservation strategy (no actuation)."""
        if not isinstance(strategy_json, str) or not strategy_json.strip():
            raise ValueError("strategy_json must be a non-empty JSON string")
        data = json.loads(strategy_json)
        if not isinstance(data, dict):
            raise ValueError("strategy_json must decode to an object")
        allowed = {
            "COMFORT_FIRST",
            "ECO_MODE",
            "UNOCCUPIED_SETBACK",
            "PRE_COOL",
            "PEAK_DEMAND_LIMIT",
            "RECOVERY",
            "HOLD_CURRENT_POLICY",
        }
        strategy = str(data.get("strategy", "HOLD_CURRENT_POLICY")).upper()
        if strategy not in allowed:
            strategy = "HOLD_CURRENT_POLICY"
        out = {
            **_pid_payload(),
            "tool": "select_energy_conservation_measure",
            "strategy": strategy,
            "target_cooling_range_c": data.get("target_cooling_range_c"),
            "control_horizon_minutes": data.get("control_horizon_minutes"),
            "confidence": data.get("confidence"),
            "reason": data.get("reason"),
            "expected_hvac_effect_pct": data.get("expected_hvac_effect_pct"),
            "note": "Supervisory selection only; deterministic optimiser + SafetyShield compute/apply setpoints.",
        }
        logger.info(
            "tool=select_energy_conservation_measure strategy=%s server_pid=%s",
            strategy,
            os.getpid(),
        )
        return json.dumps(out)

    @mcp.tool()
    def get_recent_energy_history(history_json: str = "{}") -> str:
        """Echo recent energy/history context supplied by the EnergyPlus client."""
        try:
            hist = json.loads(history_json) if history_json else {}
        except json.JSONDecodeError as exc:
            raise ValueError(f"history_json invalid: {exc}") from exc
        if not isinstance(hist, dict):
            hist = {"raw": hist}
        out = {
            **_pid_payload(),
            "tool": "get_recent_energy_history",
            "history": hist,
            "source": "client_supplied_energyplus_context",
        }
        logger.info("tool=get_recent_energy_history server_pid=%s", os.getpid())
        return json.dumps(out)

    @mcp.tool()
    def get_previous_action_outcome(outcome_json: str = "{}") -> str:
        """Return previous expected-vs-actual outcome for self-correction."""
        try:
            outcome = json.loads(outcome_json) if outcome_json else {}
        except json.JSONDecodeError as exc:
            raise ValueError(f"outcome_json invalid: {exc}") from exc
        if not isinstance(outcome, dict):
            outcome = {"raw": outcome}
        out = {
            **_pid_payload(),
            "tool": "get_previous_action_outcome",
            "outcome": outcome,
            "source": "client_supplied_self_correction",
        }
        logger.info("tool=get_previous_action_outcome server_pid=%s", os.getpid())
        return json.dumps(out)

    return mcp


def run_energyplus_experiment_stdio() -> None:
    """Entry for `TWINPILOT_MCP_MODE=energyplus_experiment`."""
    _configure_stderr_logging()
    pidfile = os.environ.get("TWINPILOT_MCP_PIDFILE", "").strip()
    if pidfile:
        Path(pidfile).write_text(str(os.getpid()))
    logger.info(
        "Starting EnergyPlus experiment MCP server pid=%s transport=stdio",
        os.getpid(),
    )
    mcp = build_energyplus_experiment_fastmcp()
    mcp.run(transport="stdio")
