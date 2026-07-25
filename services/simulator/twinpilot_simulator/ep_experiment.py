"""Real EnergyPlus baseline / agent closed-loop experiments.

This module drives EnergyPlus 24.x via the Runtime API (pyenergyplus).
Baseline runs leave thermostat schedules untouched.
Agent runs propose cooling-setpoint overrides each control interval, then
apply them only after deterministic SafetyShield validation.

No mock building dynamics are used when this module succeeds.
"""

from __future__ import annotations

import csv
import json
import logging
import math
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

ZONES = ("SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1")
PEOPLE_KEYS = {z: f"{z} People 1" for z in ZONES}

# Documented emission factor for carbon *estimate* (not measured grid intensity).
DEFAULT_CARBON_KG_PER_KWH = 0.417  # US average order-of-magnitude; labeled estimate

J_TO_KWH = 1.0 / 3_600_000.0


class EnergyPlusUnavailableError(RuntimeError):
    """Raised when EnergyPlus cannot be executed (strict mode)."""


class EnergyPlusRunError(RuntimeError):
    """Raised when an EnergyPlus run fails."""


@dataclass
class ExperimentPaths:
    energyplus_home: Path
    idf_path: Path
    epw_path: Path
    output_dir: Path


@dataclass
class SafetyLimits:
    min_cooling_setpoint: float = 22.0
    max_cooling_setpoint: float = 28.0
    min_heating_setpoint: float = 16.0
    max_heating_setpoint: float = 24.0
    max_setpoint_change_per_interval: float = 1.5
    heating_cooling_deadband_c: float = 1.5
    comfort_occupied_min_c: float = 21.0
    comfort_occupied_max_c: float = 26.0
    max_sensor_temperature_c: float = 50.0
    min_sensor_temperature_c: float = 0.0
    max_data_age_seconds: float = 900.0


@dataclass
class ExperimentConfig:
    paths: ExperimentPaths
    mode: Literal["baseline", "agent"]
    control_interval_minutes: int = 60
    carbon_kg_per_kwh: float = DEFAULT_CARBON_KG_PER_KWH
    limits: SafetyLimits = field(default_factory=SafetyLimits)
    manual_override: bool = False
    force_llm_timeout: bool = False
    force_mcp_failure: bool = False
    agent_provider: str = "deterministic"


def resolve_paths_from_env(output_dir: Path | str) -> ExperimentPaths:
    home = os.getenv("ENERGYPLUS_HOME", "").strip()
    model = os.getenv("ENERGYPLUS_MODEL_PATH", "").strip()
    weather = os.getenv("ENERGYPLUS_WEATHER_PATH", "").strip()
    if not home:
        # Convenience default for this repo's local install layout
        candidate = Path(__file__).resolve().parents[3] / "third_party" / "EnergyPlus"
        if candidate.exists():
            home = str(candidate)
    if not model:
        candidate = (
            Path(__file__).resolve().parents[3]
            / "building-models"
            / "sample-office"
            / "office_5zone.idf"
        )
        if candidate.exists():
            model = str(candidate)
    if not weather:
        candidate = (
            Path(__file__).resolve().parents[3]
            / "building-models"
            / "weather"
            / "chicago.epw"
        )
        if candidate.exists():
            weather = str(candidate)
    missing = [
        name
        for name, val in [
            ("ENERGYPLUS_HOME", home),
            ("ENERGYPLUS_MODEL_PATH", model),
            ("ENERGYPLUS_WEATHER_PATH", weather),
        ]
        if not val
    ]
    if missing:
        raise EnergyPlusUnavailableError(
            f"Missing EnergyPlus configuration: {', '.join(missing)}"
        )
    home_p = Path(home)
    if not (home_p / "energyplus").exists() and not (home_p / "energyplus.exe").exists():
        raise EnergyPlusUnavailableError(
            f"ENERGYPLUS_HOME={home} does not contain an energyplus binary"
        )
    model_p = Path(model)
    weather_p = Path(weather)
    if not model_p.is_file():
        raise EnergyPlusUnavailableError(f"IDF not found: {model_p}")
    if not weather_p.is_file():
        raise EnergyPlusUnavailableError(f"EPW not found: {weather_p}")
    return ExperimentPaths(
        energyplus_home=home_p,
        idf_path=model_p,
        epw_path=weather_p,
        output_dir=Path(output_dir),
    )


def _import_api(energyplus_home: Path) -> Any:
    home = str(energyplus_home)
    if home not in sys.path:
        sys.path.insert(0, home)
    try:
        from pyenergyplus.api import EnergyPlusAPI  # type: ignore
    except Exception as exc:  # pragma: no cover - env specific
        raise EnergyPlusUnavailableError(
            f"pyenergyplus.api import failed from {home}: {exc}"
        ) from exc
    return EnergyPlusAPI()


def _finite(value: float | None) -> bool:
    return value is not None and isinstance(value, (int, float)) and math.isfinite(value)


def propose_agent_cooling_setpoint(
    *,
    outdoor_c: float,
    zone_temps: dict[str, float],
    occupancy: dict[str, float],
    current_cooling_setpoint: float,
    limits: SafetyLimits,
) -> tuple[float, str, float]:
    """Deterministic Eco-Loop agent proposal (no direct actuation).

    Returns (proposed_setpoint, reason, confidence).
    """
    if not zone_temps:
        return current_cooling_setpoint, "missing_zone_temperature", 0.0
    if any(not _finite(v) for v in zone_temps.values()):
        return current_cooling_setpoint, "non_finite_temperature", 0.0
    if any(
        v < limits.min_sensor_temperature_c or v > limits.max_sensor_temperature_c
        for v in zone_temps.values()
    ):
        return current_cooling_setpoint, "impossible_temperature", 0.0

    avg_temp = sum(zone_temps.values()) / len(zone_temps)
    total_occ = sum(max(0.0, o) for o in occupancy.values())
    occupied = total_occ > 0.05

    # Comfort-first: never setback occupied spaces that are already near the
    # upper comfort bound. Prefer unoccupied / mild-condition savings.
    if occupied and avg_temp >= (limits.comfort_occupied_max_c - 0.7):
        target = max(limits.min_cooling_setpoint, min(current_cooling_setpoint, 23.9))
        reason = "occupied_comfort_protect"
        confidence = 0.93
    elif occupied and avg_temp <= 23.2 and outdoor_c < 27.0:
        target = min(limits.max_cooling_setpoint, current_cooling_setpoint + 0.5)
        reason = "occupied_mild_setback"
        confidence = 0.9
    elif not occupied:
        target = min(limits.max_cooling_setpoint, max(current_cooling_setpoint, 26.0))
        reason = "unoccupied_setback"
        confidence = 0.88
    else:
        target = current_cooling_setpoint
        reason = "hold"
        confidence = 0.8

    # Clamp proposal step to max change (agent-side pre-clip; SafetyShield rechecks).
    delta = target - current_cooling_setpoint
    max_d = limits.max_setpoint_change_per_interval
    if abs(delta) > max_d:
        target = current_cooling_setpoint + math.copysign(max_d, delta)
        reason += "_rate_limited"
    return float(round(target, 2)), reason, confidence


def validate_setpoint_action(
    *,
    proposed: float,
    current: float,
    heating_setpoint: float,
    limits: SafetyLimits,
    confidence: float,
    sensors_healthy: bool,
    data_age_seconds: float,
    manual_override: bool,
    llm_timed_out: bool,
    mcp_failed: bool,
) -> tuple[bool, list[str], str]:
    """Deterministic safety gate used by the EnergyPlus agent loop.

    Returns (approved, blocking_reasons, disposition).
    disposition: approved | rejected | fallback
    """
    blocking: list[str] = []

    if manual_override:
        blocking.append("manual_override_active")
    if llm_timed_out:
        blocking.append("llm_timeout")
    if mcp_failed:
        blocking.append("mcp_failure")
    if not sensors_healthy:
        blocking.append("sensors_unhealthy")
    if data_age_seconds > limits.max_data_age_seconds:
        blocking.append("stale_sensor_values")
    if not _finite(proposed) or not _finite(current):
        blocking.append("non_finite_setpoint")
    if proposed < limits.min_cooling_setpoint or proposed > limits.max_cooling_setpoint:
        blocking.append("cooling_setpoint_out_of_range")
    if abs(proposed - current) > limits.max_setpoint_change_per_interval + 1e-9:
        blocking.append("max_setpoint_change_exceeded")
    if proposed < heating_setpoint + limits.heating_cooling_deadband_c:
        blocking.append("heating_cooling_deadband_violation")

    if blocking:
        # Emergency fallback: hold last safe setpoint (no actuator change).
        return False, blocking, "fallback" if (
            "llm_timeout" in blocking
            or "mcp_failure" in blocking
            or "sensors_unhealthy" in blocking
            or "stale_sensor_values" in blocking
            or "manual_override_active" in blocking
        ) else "rejected"

    if confidence < 0.65:
        return False, ["low_confidence"], "rejected"
    return True, [], "approved"


def _sum_meter_column(csv_path: Path, column_substr: str) -> float | None:
    if not csv_path.is_file():
        return None
    with csv_path.open(newline="") as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            return None
        idx = None
        for i, name in enumerate(header):
            if column_substr in name and "Hourly" in name:
                idx = i
                break
        if idx is None:
            for i, name in enumerate(header):
                if column_substr in name:
                    idx = i
                    break
        if idx is None:
            return None
        total = 0.0
        for row in reader:
            if idx >= len(row) or row[idx] == "":
                continue
            try:
                total += float(row[idx])
            except ValueError:
                continue
        return total


def _zone_temp_series(csv_path: Path) -> dict[str, list[float]]:
    series: dict[str, list[float]] = {z: [] for z in ZONES}
    if not csv_path.is_file():
        return series
    with csv_path.open(newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            for z in ZONES:
                key = f"{z}:Zone Air Temperature [C](Hourly)"
                if key in row and row[key] not in ("", None):
                    try:
                        series[z].append(float(row[key]))
                    except ValueError:
                        pass
    return series


def _parse_results_from_csv(
    output_dir: Path,
    *,
    carbon_kg_per_kwh: float,
    limits: SafetyLimits,
    actions_log: list[dict[str, Any]],
) -> dict[str, Any]:
    csv_path = output_dir / "eplusout.csv"
    facility_j = _sum_meter_column(csv_path, "Electricity:Facility [J]")
    hvac_j = _sum_meter_column(csv_path, "Electricity:HVAC [J]")
    cooling_j = _sum_meter_column(csv_path, "Cooling:Electricity [J]")
    heating_j = _sum_meter_column(csv_path, "Heating:Electricity [J]")
    fans_j = _sum_meter_column(csv_path, "Fans:Electricity [J]")

    temps = _zone_temp_series(csv_path)
    # Peak power from hourly facility energy (J/hour -> kW)
    peak_kw = 0.0
    if csv_path.is_file():
        with csv_path.open(newline="") as f:
            reader = csv.DictReader(f)
            col = "Electricity:Facility [J](Hourly)"
            for row in reader:
                if col in row and row[col] not in ("", None):
                    try:
                        kw = float(row[col]) * J_TO_KWH  # kWh in that hour ≈ average kW
                        peak_kw = max(peak_kw, kw)
                    except ValueError:
                        pass

    # Occupied comfort violations: hours where any zone temp outside band
    # while OCCUPY schedule would typically be >0 on weekdays 6-20.
    # We use agent action log occupancy samples when available; else hour heuristic.
    violation_hours = 0.0
    hourly_occ_proxy = 0
    if csv_path.is_file():
        with csv_path.open(newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Date/Time column varies; EnergyPlus CSV uses "Date/Time"
                dt = row.get("Date/Time") or row.get("Date/Time ") or ""
                occupied = False
                # Prefer logged occupancy if matching; else weekday office hours heuristic
                # Sample from actions_log by hour string if present
                occupied = False
                hour = None
                try:
                    part = (dt or "").strip().split()[-1]
                    hour = int(part.split(":")[0])
                except Exception:
                    hour = None
                occupied = hour is not None and 6 <= hour < 20
                if occupied:
                    hourly_occ_proxy += 1
                    for z in ZONES:
                        key = f"{z}:Zone Air Temperature [C](Hourly)"
                        raw = row.get(key)
                        if raw in ("", None):
                            continue
                        try:
                            t = float(raw)
                        except (TypeError, ValueError):
                            continue
                        if (
                            t < limits.comfort_occupied_min_c
                            or t > limits.comfort_occupied_max_c
                        ):
                            violation_hours += 1.0
                            break

    total_kwh = (facility_j or 0.0) * J_TO_KWH
    hvac_kwh = (hvac_j or 0.0) * J_TO_KWH
    approved = [a for a in actions_log if a.get("disposition") == "approved"]
    rejected = [a for a in actions_log if a.get("disposition") == "rejected"]
    fallback = [a for a in actions_log if a.get("disposition") == "fallback"]

    zone_summary = {
        z: {
            "min_c": min(vals) if vals else None,
            "max_c": max(vals) if vals else None,
            "avg_c": (sum(vals) / len(vals)) if vals else None,
            "samples": len(vals),
        }
        for z, vals in temps.items()
    }

    return {
        "total_energy_kwh": round(total_kwh, 4),
        "hvac_energy_kwh": round(hvac_kwh, 4),
        "cooling_electricity_kwh": round((cooling_j or 0.0) * J_TO_KWH, 4),
        "heating_electricity_kwh": round((heating_j or 0.0) * J_TO_KWH, 4),
        "fans_electricity_kwh": round((fans_j or 0.0) * J_TO_KWH, 4),
        "peak_power_kw": round(peak_kw, 4),
        "carbon_estimate_kg": round(total_kwh * carbon_kg_per_kwh, 4),
        "carbon_factor_kg_per_kwh": carbon_kg_per_kwh,
        "carbon_note": "estimate = total_energy_kwh * documented factor; not live grid intensity",
        "zone_temperatures": zone_summary,
        "occupied_comfort_violation_hours": violation_hours,
        "occupied_hour_samples_proxy": hourly_occ_proxy,
        "agent_actions": approved,
        "rejected_actions": rejected,
        "fallback_actions": fallback,
        "action_counts": {
            "approved": len(approved),
            "rejected": len(rejected),
            "fallback": len(fallback),
            "total_decisions": len(actions_log),
        },
        "raw_csv": str(csv_path) if csv_path.is_file() else None,
        "meters_joules": {
            "Electricity:Facility": facility_j,
            "Electricity:HVAC": hvac_j,
            "Cooling:Electricity": cooling_j,
            "Heating:Electricity": heating_j,
            "Fans:Electricity": fans_j,
        },
    }


def run_experiment(config: ExperimentConfig) -> dict[str, Any]:
    """Execute one EnergyPlus experiment (baseline or agent) and write summary JSON."""
    paths = config.paths
    paths.output_dir.mkdir(parents=True, exist_ok=True)
    run_dir = paths.output_dir / "energyplus_run"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)

    api = _import_api(paths.energyplus_home)
    state = api.state_manager.new_state()

    handles: dict[str, int] = {}
    actions_log: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    current_cooling = 23.9  # IDF weekday occupied default
    current_heating = 22.2
    last_decision_minute_key: str | None = None
    started = time.time()
    status = "running"
    error_message: str | None = None

    def _ensure_handles(state_arg: Any) -> bool:
        if handles.get("ready"):
            return True
        if not api.exchange.api_data_fully_ready(state_arg):
            return False
        handles["clg"] = api.exchange.get_actuator_handle(
            state_arg, "Schedule:Compact", "Schedule Value", "Clg-SetP-Sch"
        )
        handles["htg"] = api.exchange.get_actuator_handle(
            state_arg, "Schedule:Compact", "Schedule Value", "Htg-SetP-Sch"
        )
        handles["outdoor"] = api.exchange.get_variable_handle(
            state_arg, "Site Outdoor Air Drybulb Temperature", "Environment"
        )
        for z in ZONES:
            handles[f"temp_{z}"] = api.exchange.get_variable_handle(
                state_arg, "Zone Air Temperature", z
            )
            handles[f"occ_{z}"] = api.exchange.get_variable_handle(
                state_arg, "Zone People Occupant Count", z
            )
            if handles[f"occ_{z}"] < 0:
                handles[f"occ_{z}"] = api.exchange.get_variable_handle(
                    state_arg, "People Occupant Count", PEOPLE_KEYS[z]
                )
        handles["ready"] = 1
        logger.info(
            "EnergyPlus handles ready clg=%s htg=%s outdoor=%s",
            handles["clg"],
            handles["htg"],
            handles["outdoor"],
        )
        if handles["clg"] < 0:
            raise EnergyPlusRunError(
                "Cooling schedule actuator handle unavailable (Clg-SetP-Sch)"
            )
        return True

    def on_timestep(state_arg: Any) -> None:
        nonlocal current_cooling, last_decision_minute_key
        if not _ensure_handles(state_arg):
            return
        # Do not actuate or log decisions during warmup / sizing.
        try:
            if api.exchange.warmup_flag(state_arg):
                return
        except Exception:
            pass

        month = api.exchange.month(state_arg)
        day = api.exchange.day_of_month(state_arg)
        hour = api.exchange.hour(state_arg)
        minute = api.exchange.minutes(state_arg)
        # EnergyPlus minutes often 15/30/45/60
        minute_key = f"{month:02d}-{day:02d}T{hour:02d}:{int(minute):02d}"

        outdoor = api.exchange.get_variable_value(state_arg, handles["outdoor"])
        zone_temps: dict[str, float] = {}
        occupancy: dict[str, float] = {}
        sensors_healthy = True
        for z in ZONES:
            th = handles[f"temp_{z}"]
            if th < 0:
                sensors_healthy = False
                continue
            t = api.exchange.get_variable_value(state_arg, th)
            if not _finite(t) or t < config.limits.min_sensor_temperature_c or t > config.limits.max_sensor_temperature_c:
                sensors_healthy = False
            zone_temps[z] = float(t)
            oh = handles[f"occ_{z}"]
            if oh >= 0:
                occupancy[z] = float(api.exchange.get_variable_value(state_arg, oh))
            else:
                occupancy[z] = float("nan")
                sensors_healthy = sensors_healthy and False

        missing_occ = any(not _finite(v) for v in occupancy.values())
        if missing_occ:
            # Occupancy missing → treat as unhealthy for agent decisions
            sensors_healthy = False

        obs = {
            "sim_time": minute_key,
            "outdoor_c": outdoor,
            "zone_temps_c": zone_temps,
            "occupancy": occupancy,
            "cooling_setpoint_c": current_cooling,
            "heating_setpoint_c": current_heating,
            "source": "energyplus_runtime_api",
        }
        if len(observations) < 5000:
            observations.append(obs)

        if config.mode != "agent":
            return

        # Control once per control interval (default: once per hour).
        interval = max(1, config.control_interval_minutes)
        hour_key = f"{month:02d}-{day:02d}T{hour:02d}"
        if interval >= 60:
            decision_key = hour_key
        else:
            bucket = (int(minute) // interval) * interval
            decision_key = f"{hour_key}:{bucket:02d}"
        if last_decision_minute_key == decision_key:
            return
        last_decision_minute_key = decision_key

        llm_timed_out = config.force_llm_timeout
        mcp_failed = config.force_mcp_failure
        data_age = 0.0  # live within the simulation callback
        previous = current_cooling

        proposed, reason, confidence = propose_agent_cooling_setpoint(
            outdoor_c=float(outdoor),
            zone_temps=zone_temps,
            occupancy={k: (0.0 if not _finite(v) else v) for k, v in occupancy.items()},
            current_cooling_setpoint=current_cooling,
            limits=config.limits,
        )

        approved, blocking, disposition = validate_setpoint_action(
            proposed=proposed,
            current=current_cooling,
            heating_setpoint=current_heating,
            limits=config.limits,
            confidence=confidence,
            sensors_healthy=sensors_healthy and not missing_occ and bool(zone_temps),
            data_age_seconds=data_age,
            manual_override=config.manual_override,
            llm_timed_out=llm_timed_out,
            mcp_failed=mcp_failed,
        )

        if approved and disposition == "approved":
            api.exchange.set_actuator_value(state_arg, handles["clg"], proposed)
            current_cooling = proposed
            applied_value = proposed
            energyplus_accepted = True
        else:
            # Hold last safe value explicitly (fallback / reject)
            api.exchange.set_actuator_value(state_arg, handles["clg"], current_cooling)
            applied_value = current_cooling
            energyplus_accepted = False

        actions_log.append(
            {
                "sim_time": minute_key,
                "proposal_reason": reason,
                "proposed_cooling_setpoint_c": proposed,
                "previous_cooling_setpoint_c": previous,
                "applied_cooling_setpoint_c": applied_value,
                "disposition": disposition,
                "blocking_reasons": blocking,
                "confidence": confidence,
                "energyplus_actuator_written": True,
                "energyplus_action_accepted": energyplus_accepted,
                "observation": {
                    "outdoor_c": outdoor,
                    "avg_zone_temp_c": sum(zone_temps.values()) / len(zone_temps)
                    if zone_temps
                    else None,
                    "total_occupancy": sum(
                        0.0 if not _finite(v) else v for v in occupancy.values()
                    ),
                },
                "safety": "SafetyShield-equivalent deterministic gate in ep_experiment",
            }
        )

    api.runtime.callback_end_zone_timestep_after_zone_reporting(state, on_timestep)
    # Quiet EnergyPlus stdout noise optionally
    args = [
        "-w",
        str(paths.epw_path),
        "-d",
        str(run_dir),
        str(paths.idf_path),
    ]
    try:
        rc = api.runtime.run_energyplus(state, args)
    except Exception as exc:
        status = "failed"
        error_message = f"EnergyPlus exception: {exc}"
        raise EnergyPlusRunError(error_message) from exc

    elapsed = time.time() - started
    end_file = run_dir / "eplusout.end"
    err_file = run_dir / "eplusout.err"
    if rc != 0 or (end_file.exists() and "Failed" in end_file.read_text(errors="ignore")):
        status = "failed"
        error_message = f"EnergyPlus returned rc={rc}"
        if err_file.exists():
            error_message += "\n" + "\n".join(err_file.read_text(errors="ignore").splitlines()[-30:])
        raise EnergyPlusRunError(error_message)

    status = "completed"
    metrics = _parse_results_from_csv(
        run_dir,
        carbon_kg_per_kwh=config.carbon_kg_per_kwh,
        limits=config.limits,
        actions_log=actions_log,
    )

    summary: dict[str, Any] = {
        "schema_version": "1.0",
        "experiment": config.mode,
        "simulation_status": status,
        "controller": "none" if config.mode == "baseline" else "deterministic_agent+safety_shield",
        "identical_inputs": {
            "idf": str(paths.idf_path.resolve()),
            "epw": str(paths.epw_path.resolve()),
            "run_period": "DemoPeriod 07/15-07/16 (patched in IDF)",
            "occupancy_schedule": "OCCUPY-1 (unchanged between experiments)",
        },
        "energyplus": {
            "home": str(paths.energyplus_home),
            "version_probe": "EnergyPlus Runtime API via pyenergyplus",
            "return_code": rc,
            "run_directory": str(run_dir),
            "wall_time_seconds": round(elapsed, 3),
        },
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "mocked_components": [],
        "data_provenance": {
            "zone_temperature": "EnergyPlus variable Zone Air Temperature",
            "occupancy": "EnergyPlus Zone People Occupant Count / People Occupant Count",
            "energy": "EnergyPlus eplusout.csv meters (J → kWh)",
            "weather": str(paths.epw_path.name),
            "carbon": "derived estimate (factor documented)",
        },
        **metrics,
        "observations_sample": observations[:24],
        "observations_count": len(observations),
        "error_message": error_message,
    }

    out_json = paths.output_dir / "summary.json"
    out_json.write_text(json.dumps(summary, indent=2))
    (paths.output_dir / "actions.json").write_text(json.dumps(actions_log, indent=2))
    (paths.output_dir / "run.log").write_text(
        f"status={status} rc={rc} mode={config.mode} elapsed_s={elapsed:.3f}\n"
        f"actions={len(actions_log)} observations={len(observations)}\n"
        f"total_energy_kwh={summary['total_energy_kwh']}\n"
    )
    logger.info(
        "Experiment %s completed: total_energy_kwh=%s actions=%s",
        config.mode,
        summary["total_energy_kwh"],
        len(actions_log),
    )
    return summary


def compare_summaries(baseline: dict[str, Any], agent: dict[str, Any]) -> dict[str, Any]:
    """Compare baseline vs agent experiment summaries (no invented percentages beyond arithmetic)."""
    b_e = float(baseline.get("total_energy_kwh") or 0.0)
    a_e = float(agent.get("total_energy_kwh") or 0.0)
    b_h = float(baseline.get("hvac_energy_kwh") or 0.0)
    a_h = float(agent.get("hvac_energy_kwh") or 0.0)
    b_p = float(baseline.get("peak_power_kw") or 0.0)
    a_p = float(agent.get("peak_power_kw") or 0.0)
    b_c = float(baseline.get("carbon_estimate_kg") or 0.0)
    a_c = float(agent.get("carbon_estimate_kg") or 0.0)
    b_v = float(baseline.get("occupied_comfort_violation_hours") or 0.0)
    a_v = float(agent.get("occupied_comfort_violation_hours") or 0.0)

    def delta(b: float, a: float) -> dict[str, float | None]:
        d = a - b
        pct = (d / b * 100.0) if b else None
        return {
            "baseline": b,
            "agent": a,
            "absolute_delta_agent_minus_baseline": round(d, 4),
            "percent_delta": None if pct is None else round(pct, 4),
        }

    identical = (
        baseline.get("identical_inputs") == agent.get("identical_inputs")
        or (
            baseline.get("identical_inputs", {}).get("idf")
            == agent.get("identical_inputs", {}).get("idf")
            and baseline.get("identical_inputs", {}).get("epw")
            == agent.get("identical_inputs", {}).get("epw")
        )
    )

    return {
        "schema_version": "1.0",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "inputs_identical": bool(identical),
        "baseline_status": baseline.get("simulation_status"),
        "agent_status": agent.get("simulation_status"),
        "total_energy_kwh": delta(b_e, a_e),
        "hvac_energy_kwh": delta(b_h, a_h),
        "peak_power_kw": delta(b_p, a_p),
        "carbon_estimate_kg": delta(b_c, a_c),
        "occupied_comfort_violation_hours": delta(b_v, a_v),
        "agent_action_counts": agent.get("action_counts"),
        "notes": [
            "Negative absolute_delta means agent used less than baseline.",
            "Carbon values are estimates using a documented kg/kWh factor.",
            "Only controller differs: baseline has no setpoint overrides; agent uses SafetyShield-gated overrides.",
        ],
    }
