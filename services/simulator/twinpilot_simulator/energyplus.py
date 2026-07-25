"""EnergyPlus adapter — real Runtime API when configured; no silent mock in strict mode."""

from __future__ import annotations

import logging
import os
from typing import Any

from twinpilot_simulator.base import (
    BuildingState,
    ControlActionInput,
    PlanInput,
    SimulationConfig,
    SimulationResult,
    ZoneState,
)
from twinpilot_simulator.ep_experiment import (
    EnergyPlusUnavailableError,
    ExperimentConfig,
    ExperimentPaths,
    run_experiment,
    validate_setpoint_action,
    SafetyLimits,
)
from twinpilot_simulator.mock import MockBuildingSimulator

logger = logging.getLogger(__name__)


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


class EnergyPlusAdapter:
    """Adapter around EnergyPlus.

    Behaviour:
    - ``ENERGYPLUS_STRICT=1`` (default when ``SIMULATOR_PROVIDER=energyplus``):
      never fall back silently to the mock twin. Fail loudly if EnergyPlus
      cannot run.
    - ``ENERGYPLUS_ALLOW_MOCK_FALLBACK=1``: explicit opt-in to mock fallback
      (development only). Health reports ``provider=energyplus+mock_fallback``.
    """

    def __init__(self) -> None:
        self._config = SimulationConfig()
        self._available = False
        self._error: str | None = None
        self._strict = True
        self._allow_fallback = _env_flag("ENERGYPLUS_ALLOW_MOCK_FALLBACK", False)
        self._fallback = MockBuildingSimulator()
        self._state: BuildingState | None = None
        self._last_experiment: dict[str, Any] | None = None
        self._pending_setpoints: dict[str, float] = {}

    def initialize(self, configuration: SimulationConfig) -> BuildingState:
        self._config = configuration
        # Strict by default for energyplus provider unless fallback explicitly allowed.
        self._strict = not self._allow_fallback
        home = configuration.energyplus_home or os.getenv("ENERGYPLUS_HOME")
        model = configuration.model_path or os.getenv("ENERGYPLUS_MODEL_PATH")
        weather = configuration.weather_path or os.getenv("ENERGYPLUS_WEATHER_PATH")

        if not home or not model or not weather:
            self._available = False
            self._error = "EnergyPlus environment variables not fully configured"
            return self._handle_unavailable()

        try:
            paths = ExperimentPaths(
                energyplus_home=__import__("pathlib").Path(home),
                idf_path=__import__("pathlib").Path(model),
                epw_path=__import__("pathlib").Path(weather),
                output_dir=__import__("pathlib").Path(
                    os.getenv("ENERGYPLUS_ADAPTER_RUN_DIR", "/tmp/twinpilot_ep_adapter")
                ),
            )
            # Prove EnergyPlus is executable with a baseline probe (short DemoPeriod).
            summary = run_experiment(
                ExperimentConfig(paths=paths, mode="baseline")
            )
            self._last_experiment = summary
            self._available = summary.get("simulation_status") == "completed"
            self._error = None if self._available else summary.get("error_message")
            if not self._available:
                return self._handle_unavailable()
            self._state = self._state_from_experiment(summary)
            self._state.simulated = False
            return self._state
        except Exception as exc:
            self._available = False
            self._error = f"EnergyPlus unavailable: {exc}"
            logger.exception("EnergyPlus initialize failed")
            return self._handle_unavailable()

    def _handle_unavailable(self) -> BuildingState:
        if self._strict:
            raise EnergyPlusUnavailableError(
                self._error
                or "EnergyPlus required but unavailable (strict mode; no mock fallback)"
            )
        logger.warning(
            "EnergyPlus unavailable — using MOCK fallback (explicitly allowed). error=%s",
            self._error,
        )
        state = self._fallback.initialize(self._config)
        state.simulated = True
        self._state = state
        return state

    def _state_from_experiment(self, summary: dict[str, Any]) -> BuildingState:
        zones: dict[str, ZoneState] = {}
        zt = summary.get("zone_temperatures") or {}
        for zid, stats in zt.items():
            temp = stats.get("avg_c")
            if temp is None:
                temp = 23.0
            zones[zid] = ZoneState(
                zone_id=zid,
                name=zid,
                temperature=float(temp),
                cooling_setpoint=self._pending_setpoints.get(zid, 23.9),
                heating_setpoint=22.2,
                relative_humidity=50.0,
                occupancy_count=0,
                occupancy_probability=0.0,
                co2_ppm=600.0,
                hvac_power_kw=0.0,
                lighting_power_kw=0.0,
                plug_load_power_kw=0.0,
                airflow_m3_s=0.1,
                comfort_status="unknown",
                sensor_health=1.0,
                data_freshness_seconds=0.0,
                control_status="energyplus",
                predicted_temperature=float(temp),
            )
        if not zones:
            # Should not happen on successful run; keep schema valid.
            for zid in ("SPACE1-1", "SPACE2-1", "SPACE3-1", "SPACE4-1", "SPACE5-1"):
                zones[zid] = ZoneState(
                    zone_id=zid,
                    name=zid,
                    temperature=23.0,
                    cooling_setpoint=23.9,
                    heating_setpoint=22.2,
                    relative_humidity=50.0,
                    occupancy_count=0,
                    occupancy_probability=0.0,
                    co2_ppm=600.0,
                    hvac_power_kw=0.0,
                    lighting_power_kw=0.0,
                    plug_load_power_kw=0.0,
                    airflow_m3_s=0.1,
                    comfort_status="unknown",
                    sensor_health=1.0,
                    data_freshness_seconds=0.0,
                    control_status="energyplus",
                )
        return BuildingState(
            outdoor_temperature=25.0,
            outdoor_humidity=50.0,
            solar_radiation=0.0,
            electricity_tariff=0.12,
            grid_carbon_intensity=417.0,
            total_building_power_kw=float(summary.get("peak_power_kw") or 0.0),
            peak_demand_kw=float(summary.get("peak_power_kw") or 0.0),
            zones=zones,
            simulated=False,
            step_index=0,
            timestamp_iso=str(summary.get("timestamp_utc") or ""),
        )

    def get_state(self) -> BuildingState:
        if self._state is None:
            return self.initialize(self._config)
        self._state.simulated = not self._available
        return self._state

    def simulate_plan(
        self, state: BuildingState, plan: PlanInput, horizon: int
    ) -> SimulationResult:
        if not self._available:
            if self._strict:
                raise EnergyPlusUnavailableError(
                    self._error or "EnergyPlus unavailable for simulate_plan"
                )
            result = self._fallback.simulate_plan(state, plan, horizon)
            result.metrics["energyplus"] = "fallback_mock"
            result.error_message = self._error
            return result

        # Plan evaluation for EnergyPlus mode: re-run a short agent experiment is too
        # heavy for interactive UI. We validate actions against SafetyLimits and report
        # last measured EnergyPlus metrics as the prediction anchor, clearly labeled.
        limits = SafetyLimits()
        for action in plan.actions:
            if action.action_type in {"cooling_setpoint", "request_zone_setpoint"}:
                ok, reasons, _ = validate_setpoint_action(
                    proposed=action.value,
                    current=state.zones[action.zone_id].cooling_setpoint
                    if action.zone_id in state.zones
                    else 23.9,
                    heating_setpoint=state.zones[action.zone_id].heating_setpoint
                    if action.zone_id in state.zones
                    else 22.2,
                    limits=limits,
                    confidence=0.9,
                    sensors_healthy=True,
                    data_age_seconds=0.0,
                    manual_override=False,
                    llm_timed_out=False,
                    mcp_failed=False,
                )
                if not ok:
                    return SimulationResult(
                        simulated=False,
                        status="rejected_by_safety",
                        horizon_steps=horizon,
                        energy_kwh=0.0,
                        cost=0.0,
                        carbon_kg=0.0,
                        peak_kw=0.0,
                        comfort_violation_minutes=0.0,
                        error_message="; ".join(reasons),
                        metrics={
                            "provider": "energyplus",
                            "label": "safety_rejected_before_energyplus_injection",
                            "blocking_reasons": reasons,
                        },
                    )

        base = self._last_experiment or {}
        return SimulationResult(
            simulated=False,
            status="ok",
            horizon_steps=horizon,
            energy_kwh=float(base.get("total_energy_kwh") or 0.0),
            cost=0.0,
            carbon_kg=float(base.get("carbon_estimate_kg") or 0.0),
            peak_kw=float(base.get("peak_power_kw") or 0.0),
            comfort_violation_minutes=float(
                base.get("occupied_comfort_violation_hours") or 0.0
            )
            * 60.0,
            trajectory=[state],
            metrics={
                "provider": "energyplus",
                "label": "anchored_to_last_energyplus_experiment",
                "note": (
                    "Interactive plan sim uses last EnergyPlus experiment metrics as "
                    "anchor; full closed-loop proof is scripts/run_baseline.sh + "
                    "scripts/run_agent.sh"
                ),
            },
        )

    def apply_action(self, action: ControlActionInput) -> BuildingState:
        if not self._available:
            if self._strict:
                raise EnergyPlusUnavailableError(
                    self._error or "EnergyPlus unavailable for apply_action"
                )
            return self._fallback.apply_action(action)

        state = self.get_state()
        limits = SafetyLimits()
        zone = state.zones.get(action.zone_id)
        current = zone.cooling_setpoint if zone else 23.9
        heating = zone.heating_setpoint if zone else 22.2
        ok, reasons, disposition = validate_setpoint_action(
            proposed=action.value,
            current=current,
            heating_setpoint=heating,
            limits=limits,
            confidence=0.9,
            sensors_healthy=True,
            data_age_seconds=0.0,
            manual_override=False,
            llm_timed_out=False,
            mcp_failed=False,
        )
        if not ok:
            logger.warning(
                "EnergyPlus apply_action blocked disposition=%s reasons=%s",
                disposition,
                reasons,
            )
            return state

        self._pending_setpoints[action.zone_id] = action.value
        if zone:
            zone.cooling_setpoint = action.value
            zone.control_status = "pending_energyplus_injection"
        # Full actuator injection is executed by ep_experiment agent runs.
        # Interactive apply records the approved setpoint for the next experiment.
        state.simulated = False
        self._state = state
        return state

    def reset(self) -> BuildingState:
        return self.initialize(self._config)

    def health(self) -> dict[str, Any]:
        provider = "energyplus"
        if not self._available and self._allow_fallback:
            provider = "energyplus+mock_fallback"
        elif not self._available:
            provider = "energyplus_unavailable"
        return {
            "status": "ok" if self._available else "error",
            "provider": provider,
            "available": self._available,
            "strict": self._strict,
            "allow_mock_fallback": self._allow_fallback,
            "error": self._error,
            "energyplus_home": self._config.energyplus_home or os.getenv("ENERGYPLUS_HOME"),
            "model_path": self._config.model_path or os.getenv("ENERGYPLUS_MODEL_PATH"),
            "weather_path": self._config.weather_path or os.getenv("ENERGYPLUS_WEATHER_PATH"),
            "last_experiment_status": (self._last_experiment or {}).get("simulation_status"),
            "last_experiment_total_energy_kwh": (self._last_experiment or {}).get(
                "total_energy_kwh"
            ),
        }
