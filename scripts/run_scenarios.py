#!/usr/bin/env python3
"""Run baseline/agent for multiple scenarios; write consolidated comparison."""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "services" / "simulator"), str(ROOT / "services" / "optimizer")]

from twinpilot_simulator.ep_experiment import (  # noqa: E402
    ExperimentConfig,
    ExperimentPaths,
    compare_summaries,
    resolve_paths_from_env,
    run_experiment,
)

BASE_IDF = ROOT / "building-models" / "sample-office" / "office_5zone.idf"
OUT_ROOT = ROOT / "results" / "scenarios"


SCENARIOS = {
    "normal_summer": {
        "begin_month": 7,
        "begin_day": 15,
        "end_month": 7,
        "end_day": 16,
        "occupancy_scale": 1.0,
        "description": "Normal summer DemoPeriod",
    },
    "high_occupancy": {
        "begin_month": 7,
        "begin_day": 15,
        "end_month": 7,
        "end_day": 16,
        "occupancy_scale": 1.5,
        "description": "Same weather; denser occupancy schedule fractions",
    },
    "hot_peak": {
        "begin_month": 7,
        "begin_day": 18,
        "end_month": 7,
        "end_day": 19,
        "occupancy_scale": 1.0,
        "description": "Hotter mid-summer peak window",
    },
}


def patch_idf(src: Path, dest: Path, *, begin_m: int, begin_d: int, end_m: int, end_d: int, occ_scale: float) -> None:
    text = src.read_text()
    pattern = r"  RunPeriod,\n    DemoPeriod,.*?Yes;                     !- Use Weather File Snow Indicators"
    new_rp = f"""  RunPeriod,
    DemoPeriod,              !- Name
    {begin_m},                       !- Begin Month
    {begin_d},                      !- Begin Day of Month
    ,                        !- Begin Year
    {end_m},                       !- End Month
    {end_d},                      !- End Day of Month
    ,                        !- End Year
    Tuesday,                 !- Day of Week for Start Day
    Yes,                     !- Use Weather File Holidays and Special Days
    Yes,                     !- Use Weather File Daylight Saving Period
    No,                      !- Apply Weekend Holiday Rule
    Yes,                     !- Use Weather File Rain Indicators
    Yes;                     !- Use Weather File Snow Indicators"""
    text2, n = re.subn(pattern, new_rp, text, count=1, flags=re.S)
    if n != 1:
        raise RuntimeError("Failed to patch RunPeriod for scenario IDF")

    if abs(occ_scale - 1.0) > 1e-9:
        # Scale numeric fractions inside OCCUPY-1 schedule only (best-effort).
        def scale_occupy(block: str) -> str:
            def repl(m: re.Match[str]) -> str:
                val = float(m.group(1))
                if val <= 1.0:
                    return f"{min(1.0, val * occ_scale):g}"
                return m.group(1)

            return re.sub(r"(?<=,| )\b(0?\.\d+|1(?:\.0+)?)\b", repl, block)

        m = re.search(
            r"(  Schedule:Compact,\n    OCCUPY-1,.*?;)",
            text2,
            flags=re.S,
        )
        if m:
            scaled = scale_occupy(m.group(1))
            text2 = text2[: m.start(1)] + scaled + text2[m.end(1) :]

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text2)


def run_one(name: str, cfg: dict) -> dict:
    scen_dir = OUT_ROOT / name
    if scen_dir.exists():
        shutil.rmtree(scen_dir)
    idf = scen_dir / "model.idf"
    patch_idf(
        BASE_IDF,
        idf,
        begin_m=cfg["begin_month"],
        begin_d=cfg["begin_day"],
        end_m=cfg["end_month"],
        end_d=cfg["end_day"],
        occ_scale=cfg["occupancy_scale"],
    )
    base_paths = resolve_paths_from_env(scen_dir / "baseline")
    agent_paths = resolve_paths_from_env(scen_dir / "agent")
    # Override IDF to scenario copy
    base_paths = ExperimentPaths(
        energyplus_home=base_paths.energyplus_home,
        idf_path=idf,
        epw_path=base_paths.epw_path,
        output_dir=scen_dir / "baseline",
    )
    agent_paths = ExperimentPaths(
        energyplus_home=agent_paths.energyplus_home,
        idf_path=idf,
        epw_path=agent_paths.epw_path,
        output_dir=scen_dir / "agent",
    )
    print(f"==> Scenario {name}: baseline")
    baseline = run_experiment(
        ExperimentConfig(paths=base_paths, mode="baseline", scenario=name)
    )
    print(f"==> Scenario {name}: agent")
    agent = run_experiment(
        ExperimentConfig(paths=agent_paths, mode="agent", scenario=name)
    )
    cmp = compare_summaries(baseline, agent)
    cmp["description"] = cfg["description"]
    (scen_dir / "comparison").mkdir(parents=True, exist_ok=True)
    (scen_dir / "comparison" / "comparison.json").write_text(json.dumps(cmp, indent=2))
    return {
        "scenario": name,
        "description": cfg["description"],
        "total_energy_kwh": cmp["total_energy_kwh"],
        "hvac_energy_kwh": cmp["hvac_energy_kwh"],
        "peak_power_kw": cmp["peak_power_kw"],
        "carbon_estimate_kg": cmp["carbon_estimate_kg"],
        "occupied_comfort_violation_hours": cmp["occupied_comfort_violation_hours"],
        "occupied_comfort_degree_hours": cmp["occupied_comfort_degree_hours"],
        "approved_actions": (cmp.get("agent_action_counts") or {}).get("approved"),
        "rejected_actions": (cmp.get("agent_action_counts") or {}).get("rejected"),
        "fallback_actions": (cmp.get("agent_action_counts") or {}).get("fallback"),
    }


def main() -> int:
    rows = []
    for name, cfg in SCENARIOS.items():
        rows.append(run_one(name, cfg))
    consolidated = {
        "schema_version": "1.0",
        "scenarios": rows,
        "notes": [
            "Within each scenario, baseline and agent share identical IDF/EPW/occupancy/period.",
            "Carbon is an estimate using the documented emission factor.",
            "No synthetic ×1.12 multipliers are applied.",
        ],
    }
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUT_ROOT / "consolidated_comparison.json").write_text(json.dumps(consolidated, indent=2))
    print(json.dumps(consolidated, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
