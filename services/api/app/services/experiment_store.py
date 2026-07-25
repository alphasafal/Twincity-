"""Load measured EnergyPlus experiment artifacts for dashboard / API.

Reads machine-readable JSON under results/{baseline,agent,comparison}/.
Never invents savings percentages — all deltas are arithmetic on source values.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    # services/api/app/services/experiment_store.py → repo root
    return Path(__file__).resolve().parents[4]


def results_root() -> Path:
    override = os.getenv("RESULTS_DIR", "").strip()
    if override:
        return Path(override)
    return repo_root() / "results"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def load_baseline(scenario: str = "default") -> dict[str, Any] | None:
    root = results_root()
    if scenario and scenario != "default":
        path = root / "scenarios" / scenario / "baseline" / "summary.json"
        data = _read_json(path)
        if data:
            return data
    return _read_json(root / "baseline" / "summary.json")


def load_agent(scenario: str = "default") -> dict[str, Any] | None:
    root = results_root()
    if scenario and scenario != "default":
        path = root / "scenarios" / scenario / "agent" / "summary.json"
        data = _read_json(path)
        if data:
            return data
    return _read_json(root / "agent" / "summary.json")


def load_comparison(scenario: str = "default") -> dict[str, Any] | None:
    root = results_root()
    if scenario and scenario != "default":
        path = root / "scenarios" / scenario / "comparison" / "comparison.json"
        data = _read_json(path)
        if data:
            return data
    return _read_json(root / "comparison" / "comparison.json")


def load_actions(scenario: str = "default") -> list[dict[str, Any]]:
    root = results_root()
    path = root / "agent" / "actions.json"
    if scenario and scenario != "default":
        alt = root / "scenarios" / scenario / "agent" / "actions.json"
        if alt.is_file():
            path = alt
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def load_stream_frames(scenario: str = "default") -> list[dict[str, Any]]:
    root = results_root()
    path = root / "agent" / "stream.json"
    if scenario and scenario != "default":
        alt = root / "scenarios" / scenario / "agent" / "stream.json"
        if alt.is_file():
            path = alt
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, dict) and "frames" in data:
        frames = data["frames"]
        return frames if isinstance(frames, list) else []
    return data if isinstance(data, list) else []


def load_comfort_analysis(scenario: str = "default") -> dict[str, Any] | None:
    root = results_root()
    path = root / "agent" / "comfort_analysis.json"
    if scenario and scenario != "default":
        alt = root / "scenarios" / scenario / "agent" / "comfort_analysis.json"
        if alt.is_file():
            path = alt
    return _read_json(path)


def load_consolidated_scenarios() -> dict[str, Any] | None:
    return _read_json(results_root() / "scenarios" / "consolidated_comparison.json")


def _pct_reduction(baseline: float, agent: float) -> float | None:
    if baseline == 0:
        return None
    return round((baseline - agent) / baseline * 100.0, 4)


def experiment_dashboard_payload(scenario: str = "default") -> dict[str, Any]:
    """Canonical dashboard payload derived only from experiment JSON artifacts."""
    baseline = load_baseline(scenario)
    agent = load_agent(scenario)
    comparison = load_comparison(scenario)
    actions = load_actions(scenario)
    comfort = load_comfort_analysis(scenario)

    available = bool(
        baseline
        and agent
        and baseline.get("simulation_status") == "completed"
        and agent.get("simulation_status") == "completed"
    )

    b_total = float((baseline or {}).get("total_energy_kwh") or 0.0)
    a_total = float((agent or {}).get("total_energy_kwh") or 0.0)
    b_hvac = float((baseline or {}).get("hvac_energy_kwh") or 0.0)
    a_hvac = float((agent or {}).get("hvac_energy_kwh") or 0.0)
    b_peak = float((baseline or {}).get("peak_power_kw") or 0.0)
    a_peak = float((agent or {}).get("peak_power_kw") or 0.0)
    b_comfort = float((baseline or {}).get("occupied_comfort_violation_hours") or 0.0)
    a_comfort = float((agent or {}).get("occupied_comfort_violation_hours") or 0.0)
    b_carbon = float((baseline or {}).get("carbon_estimate_kg") or 0.0)
    a_carbon = float((agent or {}).get("carbon_estimate_kg") or 0.0)
    counts = (agent or {}).get("action_counts") or {}
    if comparison and comparison.get("agent_action_counts"):
        counts = comparison["agent_action_counts"]

    payload = {
        "available": available,
        "data_mode": "energyplus",
        "data_source": "results/{baseline,agent,comparison}/*.json",
        "scenario": scenario,
        "simulated": False,
        "synthetic_multiplier_applied": False,
        "baseline": {
            "total_energy_kwh": round(b_total, 2),
            "hvac_energy_kwh": round(b_hvac, 2),
            "peak_power_kw": round(b_peak, 2),
            "carbon_estimate_kg": round(b_carbon, 2),
            "occupied_comfort_violation_hours": b_comfort,
            "comfort_degree_hours": float(
                (baseline or {}).get("occupied_comfort_degree_hours") or 0.0
            ),
        },
        "agent": {
            "total_energy_kwh": round(a_total, 2),
            "hvac_energy_kwh": round(a_hvac, 2),
            "peak_power_kw": round(a_peak, 2),
            "carbon_estimate_kg": round(a_carbon, 2),
            "occupied_comfort_violation_hours": a_comfort,
            "comfort_degree_hours": float(
                (agent or {}).get("occupied_comfort_degree_hours") or 0.0
            ),
        },
        "reductions": {
            "total_energy_pct": _pct_reduction(b_total, a_total),
            "hvac_energy_pct": _pct_reduction(b_hvac, a_hvac),
            "peak_power_pct": _pct_reduction(b_peak, a_peak),
            "carbon_estimate_pct": _pct_reduction(b_carbon, a_carbon),
            "formula": "(baseline - agent) / baseline * 100",
        },
        "action_counts": {
            "approved": int(counts.get("approved") or 0),
            "rejected": int(counts.get("rejected") or 0),
            "fallback": int(counts.get("fallback") or 0),
            "total_decisions": int(counts.get("total_decisions") or len(actions)),
        },
        "carbon_accounting": {
            "label": "estimate",
            "formula": "total_energy_kwh * emission_factor_kg_per_kwh",
            "emission_factor_kg_per_kwh": (agent or baseline or {}).get(
                "carbon_factor_kg_per_kwh", 0.417
            ),
            "units": "kg CO2e (estimate)",
            "source": "DEFAULT_CARBON_KG_PER_KWH in ep_experiment / docs/carbon.md",
            "limitations": [
                "Not live grid marginal intensity",
                "Single static factor applied to facility electricity",
            ],
        },
        "comfort_analysis": comfort,
        "comparison": comparison,
        "missing_artifacts": [
            name
            for name, present in [
                ("baseline/summary.json", baseline is not None),
                ("agent/summary.json", agent is not None),
                ("comparison/comparison.json", comparison is not None),
            ]
            if not present
        ],
    }
    return payload
