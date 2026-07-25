#!/usr/bin/env python3
"""Path C — hybrid supervisory loop.

EnergyPlus observations
  → MCP client (stdio) → separate MCP server
  → Ollama selects energy-conservation strategy
  → deterministic optimiser computes numeric setpoint
  → SafetyShield validates
  → Clg-SetP-Sch actuator
  → next EnergyPlus state
  → expected vs actual outcome logged for self-correction

Primary Path A savings remain the authoritative comfort-zero claim.
This path proves the LLM is materially involved in closed-loop decisions.
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

OUT = Path(os.environ.get("RESULTS_HYBRID_DIR", ROOT / "results" / "hybrid"))
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "stage_log.jsonl"
OUTCOME_LOG = OUT / "self_correction.jsonl"
MCP_TRACE = Path(
    os.environ.get(
        "TWINPILOT_MCP_TRACE",
        str(OUT / "mcp-runtime-trace.jsonl"),
    )
)

STRATEGIES = (
    "COMFORT_FIRST",
    "ECO_MODE",
    "UNOCCUPIED_SETBACK",
    "PRE_COOL",
    "PEAK_DEMAND_LIMIT",
    "RECOVERY",
    "HOLD_CURRENT_POLICY",
)


def log_stage(stage: str, payload: dict[str, Any], path: Path = LOG) -> None:
    row = {"ts": datetime.now(timezone.utc).isoformat(), "stage": stage, **payload}
    with path.open("a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"[{stage}] {json.dumps(payload)[:280]}", file=sys.stderr)


def call_ollama_strategy(context: dict[str, Any]) -> dict[str, Any] | None:
    base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2:1b")
    prompt = {
        "model": model,
        "stream": False,
        "format": "json",
        "prompt": (
            "You are an HVAC supervisory agent. Given building state JSON, reply ONLY with JSON:\n"
            '{"strategy": one of '
            + json.dumps(list(STRATEGIES))
            + ', "target_cooling_range_c": [low, high], '
            '"control_horizon_minutes": number, "confidence": number, "reason": string, '
            '"expected_hvac_effect_pct": number}.\n'
            "Do not invent actuators. Prefer comfort-safe strategies when occupied.\n"
            "STATE:\n" + json.dumps(context)
        ),
    }
    try:
        req = urllib.request.Request(
            f"{base}/api/generate",
            data=json.dumps(prompt).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=12) as resp:
            body = json.loads(resp.read().decode())
        parsed = json.loads(body.get("response") or "{}")
        strategy = str(parsed.get("strategy", "HOLD_CURRENT_POLICY")).upper()
        if strategy not in STRATEGIES:
            strategy = "HOLD_CURRENT_POLICY"
        conf = float(parsed.get("confidence", 0.7))
        if conf > 1.0:
            conf = conf / 100.0
        conf = max(0.0, min(1.0, conf))
        rng = parsed.get("target_cooling_range_c") or [24.0, 25.0]
        if not isinstance(rng, (list, tuple)) or len(rng) != 2:
            rng = [24.0, 25.0]
        horizon = int(parsed.get("control_horizon_minutes") or 60)
        horizon = max(30, min(120, horizon))
        out = {
            "strategy": strategy,
            "target_cooling_range_c": [float(rng[0]), float(rng[1])],
            "control_horizon_minutes": horizon,
            "confidence": conf,
            "reason": str(parsed.get("reason", "supervisory_strategy")),
            "expected_hvac_effect_pct": float(parsed.get("expected_hvac_effect_pct") or 3.0),
        }
        log_stage("ollama_strategy_proposal", {"ok": True, "model": model, "proposal": out})
        return out
    except Exception as exc:  # noqa: BLE001
        log_stage(
            "ollama_strategy_proposal",
            {"ok": False, "error": str(exc), "fallback": "HOLD_CURRENT_POLICY"},
        )
        return None


def setpoint_from_strategy(
    *,
    strategy: str,
    target_range: list[float],
    outdoor_c: float,
    zone_temps: dict[str, float],
    occupancy: dict[str, float],
    current_cooling_setpoint: float,
    limits: SafetyLimits,
    hour: int,
) -> tuple[float, str, float]:
    """Deterministic optimiser: map supervisory strategy → numeric setpoint."""
    det_sp, det_reason, det_conf = propose_agent_cooling_setpoint(
        outdoor_c=outdoor_c,
        zone_temps=zone_temps,
        occupancy=occupancy,
        current_cooling_setpoint=current_cooling_setpoint,
        limits=limits,
        hour=hour,
    )
    lo, hi = sorted(target_range[:2])
    lo = max(limits.min_cooling_setpoint, min(lo, limits.max_cooling_setpoint))
    hi = max(limits.min_cooling_setpoint, min(hi, limits.max_cooling_setpoint))
    if lo > hi:
        lo, hi = hi, lo

    total_occ = sum(max(0.0, o) for o in occupancy.values())
    occupied = total_occ > 0.05
    max_temp = max(zone_temps.values()) if zone_temps else current_cooling_setpoint

    def _rate_limited(target: float) -> float:
        delta = max(
            -limits.max_setpoint_change_per_interval,
            min(limits.max_setpoint_change_per_interval, target - current_cooling_setpoint),
        )
        bounded = current_cooling_setpoint + delta
        return max(limits.min_cooling_setpoint, min(limits.max_cooling_setpoint, bounded))

    if strategy == "HOLD_CURRENT_POLICY":
        return det_sp, f"strategy:{strategy}:{det_reason}", det_conf

    if strategy == "COMFORT_FIRST":
        target = min(det_sp, max(lo, 23.9))
        return _rate_limited(target), f"strategy:{strategy}:comfort_bias", max(det_conf, 0.9)

    if strategy == "ECO_MODE":
        eco_cap = 24.6 if occupied else min(26.5, hi)
        target = max(det_sp, min(eco_cap, hi))
        return _rate_limited(target), f"strategy:{strategy}:eco_bias", det_conf

    if strategy == "UNOCCUPIED_SETBACK":
        if not occupied:
            target = min(limits.max_cooling_setpoint, max(det_sp, hi, current_cooling_setpoint + 0.5))
            return _rate_limited(target), f"strategy:{strategy}:vacant_setback", 0.88
        return det_sp, f"strategy:{strategy}:occupied_hold:{det_reason}", det_conf

    if strategy == "PRE_COOL":
        target = min(det_sp, max(lo, 23.9))
        return _rate_limited(target), f"strategy:{strategy}:precool", 0.9

    if strategy == "PEAK_DEMAND_LIMIT":
        if outdoor_c >= 30.0:
            target = min(limits.max_cooling_setpoint, max(det_sp, hi, 24.8))
            return _rate_limited(target), f"strategy:{strategy}:peak_shed", 0.87
        return det_sp, f"strategy:{strategy}:offpeak:{det_reason}", det_conf

    if strategy == "RECOVERY":
        if max_temp >= limits.comfort_warning_c or max_temp >= 25.0:
            target = max(limits.min_cooling_setpoint, min(det_sp, 23.9))
            return _rate_limited(target), f"strategy:{strategy}:cool_recovery", 0.95
        return det_sp, f"strategy:{strategy}:stable:{det_reason}", det_conf

    return det_sp, f"strategy:{strategy}:{det_reason}", det_conf


def make_hybrid_proposal_fn(mcp_session):
    state: dict[str, Any] = {
        "last_strategy": None,
        "last_expected_pct": None,
        "last_avg_temp": None,
        "last_outdoor": None,
        "last_occ": None,
        "last_setpoint": None,
        "active_strategy": None,
        "strategy_expire_minute": -1,
        "sim_minute": 0,
        "decision_index": 0,
    }

    def _conditions_changed(outdoor_c: float, total_occ: float, avg_temp: float) -> bool:
        if state["last_outdoor"] is None:
            return True
        if abs(outdoor_c - float(state["last_outdoor"])) >= 2.0:
            return True
        if abs(total_occ - float(state["last_occ"] or 0.0)) >= 0.4:
            return True
        if abs(avg_temp - float(state["last_avg_temp"] or avg_temp)) >= 1.0:
            return True
        return False

    def proposal_fn(
        *,
        outdoor_c: float,
        zone_temps: dict[str, float],
        occupancy: dict[str, float],
        current_cooling_setpoint: float,
        limits: SafetyLimits,
        hour: int,
    ) -> tuple[float, str, float, str]:
        avg_temp = sum(zone_temps.values()) / max(1, len(zone_temps))
        total_occ = sum(max(0.0, o) for o in occupancy.values())
        # Approximate sim minute from hourly control cadence (control_interval=60 default).
        state["sim_minute"] = int(state["decision_index"]) * 60

        # Self-correction feedback from previous interval (temperature proxy for HVAC effect).
        if state["last_avg_temp"] is not None and state["last_strategy"] is not None:
            actual_delta_c = avg_temp - float(state["last_avg_temp"])
            outcome = {
                "previous_strategy": state["last_strategy"],
                "expected_hvac_effect_pct": state["last_expected_pct"],
                "actual_zone_temp_delta_c": round(actual_delta_c, 3),
                "previous_setpoint_c": state["last_setpoint"],
                "current_avg_zone_temp_c": round(avg_temp, 3),
                "comfort_proxy_safe": avg_temp <= 26.0,
                "recommendation": (
                    "retain_strategy"
                    if abs(actual_delta_c) < 0.8 and avg_temp <= 25.5
                    else "adjust_target"
                ),
            }
            log_stage("self_correction_outcome", outcome, OUTCOME_LOG)
            log_stage("self_correction_outcome", outcome)
        else:
            outcome = None

        obs = {
            "outdoor_c": outdoor_c,
            "zone_temps_c": zone_temps,
            "occupancy": occupancy,
            "cooling_setpoint_c": current_cooling_setpoint,
            "hour": hour,
            "avg_zone_temp_c": avg_temp,
            "total_occupancy": total_occ,
            "previous_outcome": outcome,
        }
        log_stage("energyplus_observation", {"hour": hour, "outdoor_c": outdoor_c, "avg_temp": avg_temp})

        try:
            obs_json = json.dumps(obs)
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
            hist_res = mcp_session.call_tool(
                "get_recent_energy_history",
                {
                    "history_json": json.dumps(
                        {
                            "last_strategy": state["last_strategy"],
                            "last_setpoint_c": state["last_setpoint"],
                            "decision_index": state["decision_index"],
                        }
                    )
                },
            )
            if outcome is not None:
                mcp_session.call_tool(
                    "get_previous_action_outcome",
                    {"outcome_json": json.dumps(outcome)},
                )
            log_stage(
                "mcp_stdio_tools",
                {
                    "ok": True,
                    "client_pid": mcp_session.client_pid,
                    "server_pid": mcp_session.server_pid,
                    "pids_differ": mcp_session.server_pid != mcp_session.client_pid,
                    "tools_called": [
                        "get_building_observation",
                        "propose_or_prepare_control_context",
                        "get_controller_constraints",
                        "get_recent_energy_history",
                        "get_previous_action_outcome",
                    ],
                    "history_ok": bool(getattr(hist_res, "ok", False)),
                },
            )
            mcp_payload = {
                "observation": obs_res.result,
                "control_context": (ctx_res.result or {}).get("context"),
                "constraints": (constraints.result or {}).get("constraints"),
                "previous_outcome": outcome,
            }
        except Exception as exc:  # noqa: BLE001
            sp, reason, conf = propose_agent_cooling_setpoint(
                outdoor_c=outdoor_c,
                zone_temps=zone_temps,
                occupancy=occupancy,
                current_cooling_setpoint=current_cooling_setpoint,
                limits=limits,
                hour=hour,
            )
            log_stage(
                "deterministic_fallback",
                {"cause": f"mcp_failure:{exc}", "proposed": sp, "reason": reason},
            )
            state.update(
                last_strategy="HOLD_CURRENT_POLICY",
                last_expected_pct=0.0,
                last_avg_temp=avg_temp,
                last_outdoor=outdoor_c,
                last_occ=total_occ,
                last_setpoint=sp,
                decision_index=state["decision_index"] + 1,
            )
            return sp, f"deterministic_fallback:mcp:{reason}", conf, "deterministic_fallback"

        need_new_strategy = (
            state["active_strategy"] is None
            or state["sim_minute"] >= int(state["strategy_expire_minute"])
            or _conditions_changed(outdoor_c, total_occ, avg_temp)
            or (
                outcome is not None
                and outcome.get("recommendation") == "adjust_target"
            )
        )

        if need_new_strategy:
            strategy_obj = call_ollama_strategy(mcp_payload)
            if strategy_obj is None:
                strategy_obj = {
                    "strategy": "HOLD_CURRENT_POLICY",
                    "target_cooling_range_c": [24.0, 25.0],
                    "control_horizon_minutes": 60,
                    "confidence": 0.7,
                    "reason": "ollama_unavailable_hold_policy",
                    "expected_hvac_effect_pct": 0.0,
                }
                log_stage(
                    "deterministic_fallback",
                    {"cause": "ollama_unavailable", "strategy": strategy_obj},
                )
            else:
                sel = mcp_session.call_tool(
                    "select_energy_conservation_measure",
                    {"strategy_json": json.dumps(strategy_obj)},
                )
                if sel.ok and isinstance(sel.result, dict) and sel.result.get("strategy"):
                    strategy_obj["strategy"] = str(sel.result["strategy"])
                log_stage(
                    "mcp_strategy_selected",
                    {
                        "strategy": strategy_obj["strategy"],
                        "horizon_min": strategy_obj.get("control_horizon_minutes"),
                        "mcp_ok": bool(getattr(sel, "ok", False)),
                    },
                )
            horizon = max(30, int(strategy_obj.get("control_horizon_minutes") or 60))
            state["active_strategy"] = strategy_obj
            state["strategy_expire_minute"] = state["sim_minute"] + horizon
        else:
            strategy_obj = dict(state["active_strategy"] or {})
            strategy_obj["reason"] = f"horizon_hold:{strategy_obj.get('strategy')}"
            log_stage(
                "strategy_horizon_hold",
                {
                    "strategy": strategy_obj.get("strategy"),
                    "expire_minute": state["strategy_expire_minute"],
                    "sim_minute": state["sim_minute"],
                },
            )

        proposed, reason, conf = setpoint_from_strategy(
            strategy=strategy_obj["strategy"],
            target_range=strategy_obj["target_cooling_range_c"],
            outdoor_c=outdoor_c,
            zone_temps=zone_temps,
            occupancy=occupancy,
            current_cooling_setpoint=current_cooling_setpoint,
            limits=limits,
            hour=hour,
        )
        conf = max(conf, float(strategy_obj.get("confidence") or 0.7))

        val = mcp_session.call_tool(
            "validate_control_action",
            {
                "proposed_setpoint_c": float(proposed),
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
                        "path": "hybrid_supervisory",
                        "strategy": strategy_obj["strategy"],
                        "proposed": proposed,
                        "reason": reason,
                        "expected_hvac_effect_pct": strategy_obj.get("expected_hvac_effect_pct"),
                    }
                )
            },
        )
        log_stage(
            "hybrid_decision",
            {
                "strategy": strategy_obj["strategy"],
                "proposed_setpoint_c": proposed,
                "reason": reason,
                "mcp_validate_ok": bool(getattr(val, "ok", False)),
                "expected_hvac_effect_pct": strategy_obj.get("expected_hvac_effect_pct"),
            },
        )

        state.update(
            last_strategy=strategy_obj["strategy"],
            last_expected_pct=strategy_obj.get("expected_hvac_effect_pct"),
            last_avg_temp=avg_temp,
            last_outdoor=outdoor_c,
            last_occ=total_occ,
            last_setpoint=proposed,
            decision_index=state["decision_index"] + 1,
        )
        if strategy_obj.get("reason") == "ollama_unavailable_hold_policy":
            source = "deterministic_fallback"
        else:
            source = "hybrid_supervisory"
        return float(proposed), reason, float(conf), source

    return proposal_fn


def main() -> int:
    if LOG.exists():
        LOG.unlink()
    if OUTCOME_LOG.exists():
        OUTCOME_LOG.unlink()
    if MCP_TRACE.exists():
        MCP_TRACE.unlink()

    mcp_session = open_energyplus_mcp_session(trace_path=MCP_TRACE, timeout_s=20.0)
    try:
        tools = mcp_session.list_tools()
        log_stage(
            "mcp_session_ready",
            {
                "transport": "stdio",
                "client_pid": mcp_session.client_pid,
                "server_pid": mcp_session.server_pid,
                "pids_differ": mcp_session.server_pid != mcp_session.client_pid,
                "tools": tools,
            },
        )

        baseline_paths = resolve_paths_from_env(OUT / "baseline")
        agent_paths = resolve_paths_from_env(OUT / "agent")

        baseline = run_experiment(
            ExperimentConfig(paths=baseline_paths, mode="baseline", scenario="hybrid_supervisory")
        )
        log_stage("baseline_complete", {"total_energy_kwh": baseline.get("total_energy_kwh")})

        agent = run_experiment(
            ExperimentConfig(
                paths=agent_paths,
                mode="agent",
                scenario="hybrid_supervisory",
                agent_provider="hybrid_supervisory",
                proposal_fn=make_hybrid_proposal_fn(mcp_session),
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

        # Safety demo: 35C still rejected
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
            {"proposed": 35.0, "approved": ok, "disposition": disposition, "reasons": reasons},
        )

        # Strategy histogram from stage log
        strategies: dict[str, int] = {}
        if LOG.exists():
            for line in LOG.read_text().splitlines():
                row = json.loads(line)
                if row.get("stage") == "hybrid_decision":
                    s = row.get("strategy") or "UNKNOWN"
                    strategies[s] = strategies.get(s, 0) + 1

        summary = {
            "path": "hybrid_supervisory",
            "description": (
                "Ollama selects ECM/strategy via MCP tools; deterministic optimiser "
                "computes setpoints; SafetyShield remains authoritative."
            ),
            "mcp_transport": "stdio",
            "mcp_client_pid": mcp_session.client_pid,
            "mcp_server_pid": mcp_session.server_pid,
            "mcp_pids_differ": mcp_session.server_pid != mcp_session.client_pid,
            "baseline": {
                "total_energy_kwh": baseline.get("total_energy_kwh"),
                "hvac_energy_kwh": baseline.get("hvac_energy_kwh"),
                "peak_power_kw": baseline.get("peak_power_kw"),
                "occupied_comfort_violation_hours": baseline.get(
                    "occupied_comfort_violation_hours"
                ),
                "status": baseline.get("simulation_status"),
            },
            "agent": {
                "total_energy_kwh": agent.get("total_energy_kwh"),
                "hvac_energy_kwh": agent.get("hvac_energy_kwh"),
                "peak_power_kw": agent.get("peak_power_kw"),
                "occupied_comfort_violation_hours": agent.get(
                    "occupied_comfort_violation_hours"
                ),
                "action_counts": agent.get("action_counts"),
                "controller": agent.get("controller"),
                "status": agent.get("simulation_status"),
            },
            "strategy_counts": strategies,
            "self_correction_log": str(OUTCOME_LOG),
            "stage_log": str(LOG),
            "mcp_trace": str(MCP_TRACE),
            "authoritative_savings_claim": "Path A comfort-zero deterministic experiment",
            "notes": [
                "Path C proves LLM supervisory involvement in the closed loop.",
                "Numeric setpoints are computed by the deterministic optimiser.",
                "SafetyShield retains final authority before Clg-SetP-Sch writes.",
                "Self-correction outcomes are logged in self_correction.jsonl.",
            ],
        }
        (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
        print(json.dumps(summary, indent=2))
        return 0
    finally:
        mcp_session.close()


if __name__ == "__main__":
    raise SystemExit(main())
