"""Real EnergyPlus baseline / agent closed-loop experiments (Path A core).

This module drives EnergyPlus 24.x via the Runtime API (pyenergyplus).

Engineer map
------------
- ``run_experiment`` — full co-sim loop (baseline or agent)
- ``propose_agent_cooling_setpoint`` — deterministic Eco-Loop proposal (no actuation)
- ``validate_setpoint_action`` — hard safety gate before any actuator write
- Actuator used: Schedule:Compact ``Clg-SetP-Sch`` via ``set_actuator_value``

Baseline runs leave thermostat schedules untouched.
Agent runs propose cooling-setpoint overrides each control interval, then
apply them only after deterministic SafetyShield validation.

No mock building dynamics are used when this module succeeds.
Authoritative savings numbers come from comparing baseline vs agent summaries.
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
    """Hard limits enforced by ``validate_setpoint_action`` (EnergyPlus loop).

    These are intentionally independent of the LLM — the model cannot widen them.
    """

    min_cooling_setpoint: float = 22.0
    max_cooling_setpoint: float = 28.0
    min_heating_setpoint: float = 16.0
    max_heating_setpoint: float = 24.0
    max_setpoint_change_per_interval: float = 1.0
    heating_cooling_deadband_c: float = 1.5
    comfort_occupied_min_c: float = 21.0
    comfort_occupied_max_c: float = 26.0
    comfort_warning_c: float = 25.3
    max_occupied_cooling_setpoint: float = 24.8
    max_unoccupied_cooling_setpoint: float = 25.8
    max_sensor_temperature_c: float = 50.0
    min_sensor_temperature_c: float = 0.0
    max_data_age_seconds: float = 900.0


@dataclass
class ExperimentConfig:
    """Configuration for one EnergyPlus experiment run.

    ``proposal_fn`` — optional external proposer (Path B/C). Signature must match
    what ``run_experiment`` calls each control interval. If ``None``, Path A uses
    ``propose_agent_cooling_setpoint``.
    """

    paths: ExperimentPaths
    mode: Literal["baseline", "agent"]
    control_interval_minutes: int = 60
    carbon_kg_per_kwh: float = DEFAULT_CARBON_KG_PER_KWH
    limits: SafetyLimits = field(default_factory=SafetyLimits)
    manual_override: bool = False
    force_llm_timeout: bool = False
    force_mcp_failure: bool = False
    agent_provider: str = "deterministic"  # deterministic | llm_mcp
    scenario: str = "default"
    inject_unsafe_proposal: bool = False  # safety demo only — not for efficiency runs
    record_stream: bool = True
    proposal_fn: Any | None = None  # optional external proposer (LLM/MCP)


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
    hour: int | None = None,
) -> tuple[float, str, float]:
    """Deterministic Eco-Loop agent proposal (Path A). Does **not** actuate.

    Policy (comfort-first, then savings):
    1. Reject impossible / missing sensors.
    2. Morning pre-cool / pre-emptive recovery near comfort warning.
    3. Mild occupied setback when cool enough (primary HVAC saver).
    4. Unoccupied night setback toward higher cooling setpoint.
    5. Agent-side rate-limit; SafetyShield re-checks before write.

    Returns:
        ``(proposed_setpoint_c, reason_code, confidence)``
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
    max_temp = max(zone_temps.values())
    hottest_zone = max(zone_temps.items(), key=lambda kv: kv[1])[0]
    total_occ = sum(max(0.0, o) for o in occupancy.values())
    occupied = total_occ > 0.05
    office_hours = hour is not None and 6 <= hour < 20
    # Comfort protection uses office-hours; energy setbacks use measured occupancy.
    comfort_guard = occupied or office_hours

    # Respect heating/cooling deadband in proposals (heating schedule ~22.2 °C).
    min_cool_vs_heat = 22.2 + limits.heating_cooling_deadband_c  # 23.7

    # Pre-cooling just before busy morning to avoid 10:00 overshoot seen previously.
    if hour is not None and hour in {8, 9} and outdoor_c >= 24.0 and max_temp >= 24.5:
        target = max(min_cool_vs_heat, 23.9)
        reason = "pre_cooling_morning"
        confidence = 0.92
    # Pre-emptive recovery when approaching comfort warning
    elif comfort_guard and max_temp >= limits.comfort_warning_c:
        target = max(min_cool_vs_heat, 23.9)
        reason = f"preemptive_recovery_{hottest_zone}"
        confidence = 0.95
    # Occupied-zone priority when warming under load
    elif comfort_guard and max_temp >= 25.0:
        target = max(min_cool_vs_heat, 23.9)
        reason = "occupied_zone_priority"
        confidence = 0.94
    elif comfort_guard and avg_temp <= 23.5 and outdoor_c < 28.0 and max_temp < 25.0:
        # Daytime mild setback — primary HVAC saver vs fixed 23.9 °C occupied schedule
        target = min(25.0, max(current_cooling_setpoint, 24.4))
        reason = "occupied_mild_setback"
        confidence = 0.9
    elif not comfort_guard:
        # Night/vacant: step toward high setback (rate-limited below)
        target = min(limits.max_cooling_setpoint, current_cooling_setpoint + 1.0)
        if target < 27.0:
            target = min(limits.max_cooling_setpoint, max(target, current_cooling_setpoint + 1.0))
        reason = "unoccupied_setback"
        confidence = 0.88
    else:
        target = 24.2
        reason = "hold_occupied_cap"
        confidence = 0.82

    if comfort_guard:
        # Hard cap during occupied/office hours to protect comfort band
        target = min(target, 25.0)
    target = max(target, min_cool_vs_heat)

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

    This is the hard gate before ``Clg-SetP-Sch`` writes. The LLM cannot bypass it.
    Typical rejects: out of [22, 28]°C, change > 1°C/interval, deadband vs heating,
    stale/unhealthy sensors, manual override. LLM/MCP timeouts force fallback
    disposition rather than blind actuation.

    Returns:
        ``(approved, blocking_reasons, disposition)`` where disposition is one of
        ``approved`` | ``rejected`` | ``fallback``.
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

    # Occupied comfort violations + degree-hours (office-hours proxy 06:00–20:00).
    violation_hours = 0.0
    degree_hours = 0.0
    hourly_occ_proxy = 0
    violation_events: list[dict[str, Any]] = []
    if csv_path.is_file():
        with csv_path.open(newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                dt = row.get("Date/Time") or row.get("Date/Time ") or ""
                hour = None
                try:
                    part = (dt or "").strip().split()[-1]
                    hour = int(part.split(":")[0])
                except Exception:
                    hour = None
                occupied = hour is not None and 6 <= hour < 20
                if not occupied:
                    continue
                hourly_occ_proxy += 1
                hour_violated = False
                worst: dict[str, Any] | None = None
                for z in ZONES:
                    key = f"{z}:Zone Air Temperature [C](Hourly)"
                    raw = row.get(key)
                    if raw in ("", None):
                        continue
                    try:
                        t = float(raw)
                    except (TypeError, ValueError):
                        continue
                    low = limits.comfort_occupied_min_c
                    high = limits.comfort_occupied_max_c
                    if t < low or t > high:
                        hour_violated = True
                        if t > high:
                            dev = t - high
                            bound = "max"
                        else:
                            dev = low - t
                            bound = "min"
                        degree_hours += dev
                        cand = {
                            "timestamp": (dt or "").strip(),
                            "zone": z,
                            "occupancy_proxy": "office_hours_06_20",
                            "boundary": bound,
                            "boundary_c": high if bound == "max" else low,
                            "actual_temperature_c": round(t, 4),
                            "maximum_deviation_c": round(dev, 4),
                            "duration_hours": 1.0,
                            "degree_hours": round(dev, 4),
                        }
                        if worst is None or cand["maximum_deviation_c"] > worst["maximum_deviation_c"]:
                            worst = cand
                if hour_violated:
                    violation_hours += 1.0
                    if worst:
                        violation_events.append(worst)

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

    comfort_analysis = {
        "occupied_comfort_violation_hours": violation_hours,
        "occupied_comfort_degree_hours": round(degree_hours, 4),
        "comfort_band_c": {
            "min": limits.comfort_occupied_min_c,
            "max": limits.comfort_occupied_max_c,
            "warning": limits.comfort_warning_c,
        },
        "events": violation_events,
        "severity_note": (
            "degree-hours = sum of |T - band| over occupied hours with violations"
        ),
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
        "occupied_comfort_degree_hours": round(degree_hours, 4),
        "occupied_hour_samples_proxy": hourly_occ_proxy,
        "comfort_analysis": comfort_analysis,
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
    """Execute one EnergyPlus experiment (baseline or agent) and write summary JSON.

    Control loop (agent mode), each control interval after warmup:
    1. Read outdoor temp, zone temps, occupancy from EnergyPlus variables.
    2. Call ``proposal_fn`` or ``propose_agent_cooling_setpoint``.
    3. ``validate_setpoint_action`` — reject/fallback → keep prior setpoint.
    4. On approve: ``api.exchange.set_actuator_value`` on ``Clg-SetP-Sch``.
    5. Log action + following timestep temperatures for closed-loop proof.

    Baseline mode skips proposal/actuation and only collects meters/comfort.
    Outputs land under ``config.paths.output_dir`` (summary.json, actions.json, …).
    """
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
    stream_frames: list[dict[str, Any]] = []
    current_cooling = 23.9  # IDF weekday occupied default
    current_heating = 22.2
    last_decision_minute_key: str | None = None
    unsafe_injected = False
    started = time.time()
    status = "running"
    error_message: str | None = None
    controller_mode = config.agent_provider if config.mode == "agent" else "none"

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
        # Temperature is required; occupancy may fall back to office-hours proxy.
        temp_ok = sensors_healthy and bool(zone_temps)

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
            if config.record_stream and int(minute) in (0, 60) and len(stream_frames) < 2000:
                stream_frames.append(
                    {
                        "timestamp": minute_key,
                        "zone_temperatures_c": zone_temps,
                        "occupancy": {
                            k: (None if not _finite(v) else v) for k, v in occupancy.items()
                        },
                        "weather_outdoor_c": outdoor,
                        "energy_power_kw": None,
                        "current_setpoint_c": current_cooling,
                        "proposed_setpoint_c": None,
                        "controller_mode": "baseline_fixed_schedule",
                        "safety_shield_result": "n/a",
                        "executed_action": "none",
                        "next_simulation_state": "energyplus_advances",
                    }
                )
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
        proposal_source = controller_mode

        occ_clean = {k: (0.0 if not _finite(v) else v) for k, v in occupancy.items()}
        if config.proposal_fn is not None:
            proposed, reason, confidence, proposal_source = config.proposal_fn(
                outdoor_c=float(outdoor),
                zone_temps=zone_temps,
                occupancy=occ_clean,
                current_cooling_setpoint=current_cooling,
                limits=config.limits,
                hour=int(hour),
            )
        else:
            proposed, reason, confidence = propose_agent_cooling_setpoint(
                outdoor_c=float(outdoor),
                zone_temps=zone_temps,
                occupancy=occ_clean,
                current_cooling_setpoint=current_cooling,
                limits=config.limits,
                hour=int(hour),
            )

        # Optional one-shot unsafe proposal for safety demonstration runs only.
        if config.inject_unsafe_proposal and not unsafe_injected:
            proposed = 35.0
            reason = "intentional_unsafe_demo_proposal"
            confidence = 0.99
            unsafe_injected = True
            proposal_source = "safety_demo"

        approved, blocking, disposition = validate_setpoint_action(
            proposed=proposed,
            current=current_cooling,
            heating_setpoint=current_heating,
            limits=config.limits,
            confidence=confidence,
            sensors_healthy=temp_ok,
            data_age_seconds=data_age,
            manual_override=config.manual_override,
            llm_timed_out=llm_timed_out,
            mcp_failed=mcp_failed,
        )

        apply_approved = approved and disposition == "approved"
        if apply_approved:
            api.exchange.set_actuator_value(state_arg, handles["clg"], proposed)
            current_cooling = proposed
            applied_value = proposed
            energyplus_accepted = True
            executed = f"set_clg_setpoint={proposed}"
        else:
            # Hold last safe value explicitly (fallback / reject)
            api.exchange.set_actuator_value(state_arg, handles["clg"], current_cooling)
            applied_value = current_cooling
            energyplus_accepted = False
            executed = f"hold_safe_setpoint={current_cooling}"

        # LLM-path deterministic substitute: count as fallback even when the
        # substitute setpoint itself passes the safety gate and is applied.
        if str(proposal_source).startswith("deterministic_fallback"):
            disposition = "fallback"

        action_record = {
            "sim_time": minute_key,
            "proposal_reason": reason,
            "proposal_source": proposal_source,
            "proposed_cooling_setpoint_c": proposed,
            "previous_cooling_setpoint_c": previous,
            "applied_cooling_setpoint_c": applied_value,
            "disposition": disposition,
            "blocking_reasons": blocking,
            "confidence": confidence,
            "controller_mode": controller_mode,
            "energyplus_actuator_written": True,
            "energyplus_action_accepted": energyplus_accepted,
            "observation": {
                "outdoor_c": outdoor,
                "avg_zone_temp_c": sum(zone_temps.values()) / len(zone_temps)
                if zone_temps
                else None,
                "max_zone_temp_c": max(zone_temps.values()) if zone_temps else None,
                "total_occupancy": sum(occ_clean.values()),
                "missing_occupancy": missing_occ,
            },
            "safety": "SafetyShield-equivalent deterministic gate in ep_experiment",
        }
        actions_log.append(action_record)

        if config.record_stream and len(stream_frames) < 2000:
            stream_frames.append(
                {
                    "timestamp": minute_key,
                    "zone_temperatures_c": zone_temps,
                    "occupancy": {
                        k: (None if not _finite(v) else v) for k, v in occupancy.items()
                    },
                    "weather_outdoor_c": outdoor,
                    "energy_power_kw": None,
                    "current_setpoint_c": previous,
                    "proposed_setpoint_c": proposed,
                    "controller_mode": controller_mode,
                    "safety_shield_result": {
                        "disposition": disposition,
                        "blocking_reasons": blocking,
                        "approved": approved,
                    },
                    "executed_action": executed,
                    "next_simulation_state": {
                        "cooling_setpoint_c": applied_value,
                        "energyplus_action_accepted": energyplus_accepted,
                    },
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
        "scenario": config.scenario,
        "controller": (
            "none"
            if config.mode == "baseline"
            else f"{controller_mode}+safety_shield"
        ),
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
        "stream_frame_count": len(stream_frames),
        "error_message": error_message,
    }

    out_json = paths.output_dir / "summary.json"
    out_json.write_text(json.dumps(summary, indent=2))
    (paths.output_dir / "actions.json").write_text(json.dumps(actions_log, indent=2))
    if metrics.get("comfort_analysis") is not None:
        (paths.output_dir / "comfort_analysis.json").write_text(
            json.dumps(metrics["comfort_analysis"], indent=2)
        )
    if config.record_stream:
        (paths.output_dir / "stream.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "mode": config.mode,
                    "scenario": config.scenario,
                    "frames": stream_frames,
                },
                indent=2,
            )
        )
    (paths.output_dir / "run.log").write_text(
        f"status={status} rc={rc} mode={config.mode} scenario={config.scenario} "
        f"elapsed_s={elapsed:.3f}\n"
        f"actions={len(actions_log)} observations={len(observations)} "
        f"stream_frames={len(stream_frames)}\n"
        f"total_energy_kwh={summary['total_energy_kwh']}\n"
        f"comfort_violation_hours={summary.get('occupied_comfort_violation_hours')}\n"
        f"comfort_degree_hours={summary.get('occupied_comfort_degree_hours')}\n"
    )
    # Persist a compact EnergyPlus runtime log excerpt for evidence packs.
    if err_file.exists():
        (paths.output_dir / "energyplus-runtime.log").write_text(
            err_file.read_text(errors="ignore")
        )
    logger.info(
        "Experiment %s completed: total_energy_kwh=%s actions=%s comfort_h=%s",
        config.mode,
        summary["total_energy_kwh"],
        len(actions_log),
        summary.get("occupied_comfort_violation_hours"),
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
    b_dh = float(baseline.get("occupied_comfort_degree_hours") or 0.0)
    a_dh = float(agent.get("occupied_comfort_degree_hours") or 0.0)

    def delta(b: float, a: float) -> dict[str, float | None]:
        d = a - b
        pct = ((b - a) / b * 100.0) if b else None  # reduction % (positive = improvement)
        return {
            "baseline": b,
            "agent": a,
            "absolute_delta_agent_minus_baseline": round(d, 4),
            "percent_reduction": None if pct is None else round(pct, 4),
            # keep legacy key for compatibility
            "percent_delta": None if b == 0 else round(d / b * 100.0, 4),
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
        "schema_version": "1.1",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "scenario": agent.get("scenario") or baseline.get("scenario") or "default",
        "inputs_identical": bool(identical),
        "baseline_status": baseline.get("simulation_status"),
        "agent_status": agent.get("simulation_status"),
        "total_energy_kwh": delta(b_e, a_e),
        "hvac_energy_kwh": delta(b_h, a_h),
        "peak_power_kw": delta(b_p, a_p),
        "carbon_estimate_kg": delta(b_c, a_c),
        "occupied_comfort_violation_hours": delta(b_v, a_v),
        "occupied_comfort_degree_hours": delta(b_dh, a_dh),
        "agent_action_counts": agent.get("action_counts"),
        "carbon_accounting": {
            "label": "estimate",
            "formula": "total_energy_kwh * emission_factor_kg_per_kwh",
            "emission_factor_kg_per_kwh": agent.get("carbon_factor_kg_per_kwh")
            or baseline.get("carbon_factor_kg_per_kwh"),
            "units": "kg CO2e (estimate)",
        },
        "notes": [
            "percent_reduction = (baseline - agent) / baseline * 100 (positive means agent used less).",
            "Carbon values are estimates using a documented kg/kWh factor.",
            "Only controller differs: baseline has no setpoint overrides; agent uses SafetyShield-gated overrides.",
            "Synthetic multipliers (e.g. ×1.12) are not used.",
        ],
    }
