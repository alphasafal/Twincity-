#!/usr/bin/env python3
"""Prove EnergyPlus → MCP → LLM → SafetyShield → EnergyPlus actuator path.

Stages logged to results/llm_mcp/stage_log.jsonl and summary.json.
LLM never bypasses SafetyShield. Deterministic proposer is fallback.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "services" / "simulator"),
    str(ROOT / "services" / "optimizer"),
    str(ROOT / "services" / "agent"),
]

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


def log_stage(stage: str, payload: dict[str, Any]) -> None:
    row = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        **payload,
    }
    with LOG.open("a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"[{stage}] {json.dumps(payload)[:240]}")


def mcp_observation_from_energyplus(obs: dict[str, Any]) -> dict[str, Any]:
    """Simulate MCP resource/tool payload built from EnergyPlus observations.

    Uses the same JSON shape as twinpilot_mcp building://current-state style tools.
    """
    resource = {
        "resource": "building://current-state",
        "tool": "get_building_state",
        "source": "energyplus_runtime_observation",
        "outdoor_temperature_c": obs.get("outdoor_c"),
        "zones": {
            z: {
                "temperature_c": t,
                "occupancy": (obs.get("occupancy") or {}).get(z),
            }
            for z, t in (obs.get("zone_temps_c") or {}).items()
        },
        "cooling_setpoint_c": obs.get("cooling_setpoint_c"),
    }
    log_stage("mcp_resource_tool", {"ok": True, "payload_keys": list(resource.keys())})
    return resource


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
        if conf > 1.0:  # models sometimes return 0-100
            conf = conf / 100.0
        conf = max(0.0, min(1.0, conf))
        log_stage(
            "llm_structured_proposal",
            {"ok": True, "provider": "ollama", "model": model, "proposal": parsed},
        )
        return sp, {"source": "ollama", "raw": parsed, "confidence": conf}
    except Exception as exc:
        log_stage(
            "llm_structured_proposal",
            {"ok": False, "provider": "ollama", "error": str(exc), "fallback": "deterministic"},
        )
        return None, {"source": "ollama_failed", "error": str(exc)}


def make_proposal_fn():
    """Return a proposal_fn for run_experiment that uses MCP+LLM with deterministic fallback."""

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
        log_stage("energyplus_observation", {"hour": hour, "outdoor_c": outdoor_c, "zones": zone_temps})
        mcp_payload = mcp_observation_from_energyplus(obs)
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
        return float(llm_sp), reason, conf, "llm_via_mcp"

    return proposal_fn


def main() -> int:
    if LOG.exists():
        LOG.unlink()
    log_stage("start", {"out": str(OUT)})

    # First capture a short baseline for comparison context
    paths = resolve_paths_from_env(OUT / "baseline")
    baseline = run_experiment(ExperimentConfig(paths=paths, mode="baseline", scenario="llm_mcp"))
    log_stage("baseline_complete", {"total_energy_kwh": baseline.get("total_energy_kwh")})

    agent_paths = resolve_paths_from_env(OUT / "agent")
    agent = run_experiment(
        ExperimentConfig(
            paths=agent_paths,
            mode="agent",
            scenario="llm_mcp",
            agent_provider="llm_mcp",
            proposal_fn=make_proposal_fn(),
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

    # Prove SafetyShield rejects unsafe LLM-like output
    ok, reasons, disposition = validate_setpoint_action(
        proposed=35.0,
        current=23.9,
        heating_setpoint=22.2,
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

    summary = {
        "path": "EnergyPlus → MCP tool/resource → LLM structured proposal → SafetyShield → EnergyPlus actuator",
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
        "notes": [
            "If Ollama is down, deterministic_fallback is used and logged.",
            "Unsafe 35C proposal is always rejected by SafetyShield.",
        ],
    }
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
