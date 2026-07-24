"""Deterministic MockBuildingSimulator for fully offline demos."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

from twinpilot_simulator.base import (
    BuildingState,
    ControlActionInput,
    PlanInput,
    SimulationConfig,
    SimulationResult,
    ZoneState,
)

ZONE_SEEDS = {
    "core": {
        "name": "Core Office",
        "temperature": 23.2,
        "cooling_setpoint": 23.0,
        "heating_setpoint": 21.0,
        "occupancy_count": 42,
        "sensor_health": 0.98,
        "area": 450.0,
    },
    "north": {
        "name": "North Office",
        "temperature": 23.8,
        "cooling_setpoint": 23.5,
        "heating_setpoint": 21.0,
        "occupancy_count": 18,
        "sensor_health": 0.96,
        "area": 280.0,
    },
    "south": {
        "name": "South Office",
        "temperature": 24.4,
        "cooling_setpoint": 24.0,
        "heating_setpoint": 21.0,
        "occupancy_count": 31,
        "sensor_health": 0.95,
        "area": 300.0,
    },
    "east": {
        "name": "East Office",
        "temperature": 23.5,
        "cooling_setpoint": 23.5,
        "heating_setpoint": 21.0,
        "occupancy_count": 22,
        "sensor_health": 0.97,
        "area": 260.0,
    },
    "west": {
        "name": "West Office",
        "temperature": 24.7,
        "cooling_setpoint": 24.0,
        "heating_setpoint": 21.0,
        "occupancy_count": 28,
        "sensor_health": 0.94,
        "area": 270.0,
    },
}


class MockBuildingSimulator:
    """Simplified thermal dynamics with seeded noise."""

    def __init__(self) -> None:
        self._config = SimulationConfig()
        self._rng = np.random.default_rng(42)
        self._state: BuildingState | None = None
        self._overrides: dict[str, dict[str, Any]] = {}
        self._faults: dict[str, Any] = {}
        self._speed = 1
        self._paused = False
        self._scenario: str | None = None
        self._base_time = datetime(2026, 7, 24, 10, 0, tzinfo=timezone.utc)

    def initialize(self, configuration: SimulationConfig) -> BuildingState:
        self._config = configuration
        self._rng = np.random.default_rng(configuration.seed)
        self._overrides = {}
        self._faults = {}
        self._paused = False
        self._speed = 1
        self._state = self._initial_state()
        return deepcopy(self._state)

    def get_state(self) -> BuildingState:
        if self._state is None:
            self.initialize(SimulationConfig())
        assert self._state is not None
        return deepcopy(self._state)

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok",
            "provider": "mock",
            "simulated": True,
            "paused": self._paused,
            "speed": self._speed,
            "scenario": self._scenario,
            "step_index": self._state.step_index if self._state else 0,
        }

    def reset(self) -> BuildingState:
        return self.initialize(self._config)

    def set_speed(self, speed: int) -> None:
        if speed not in {1, 5, 15, 60}:
            raise ValueError("Speed must be one of 1, 5, 15, 60")
        self._speed = speed

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def inject_fault(self, zone_id: str, fault_type: str, value: float | None = None) -> None:
        self._faults[zone_id] = {"type": fault_type, "value": value}

    def clear_faults(self) -> None:
        self._faults = {}

    def set_scenario_modifiers(self, modifiers: dict[str, Any]) -> None:
        self._scenario = modifiers.get("scenario_id")
        if "outdoor_temperature" in modifiers:
            assert self._state
            self._state.outdoor_temperature = float(modifiers["outdoor_temperature"])
        if "carbon_intensity" in modifiers:
            assert self._state
            self._state.grid_carbon_intensity = float(modifiers["carbon_intensity"])
        if "occupancy_spike" in modifiers:
            spike = modifiers["occupancy_spike"]
            zid = spike["zone_id"]
            if self._state and zid in self._state.zones:
                self._state.zones[zid].occupancy_count = int(spike["occupancy"])
                self._state.zones[zid].occupancy_probability = 0.98

    def apply_action(self, action: ControlActionInput) -> BuildingState:
        state = self.get_state()
        zone = state.zones.get(action.zone_id)
        if zone is None:
            raise KeyError(f"Unknown zone {action.zone_id}")
        if action.action_type in {"cooling_setpoint", "request_zone_setpoint"}:
            zone.cooling_setpoint = float(action.value)
            zone.control_status = "OVERRIDE"
        elif action.action_type == "heating_setpoint":
            zone.heating_setpoint = float(action.value)
            zone.control_status = "OVERRIDE"
        elif action.action_type == "hvac_schedule":
            zone.control_status = "SCHEDULE_UPDATED"
        else:
            # Extensible adapters for remaining controls
            self._overrides.setdefault(action.zone_id, {})[action.action_type] = action.value
            zone.control_status = "EXTENDED_CONTROL"
        self._state = state
        return deepcopy(state)

    def step(self, n: int = 1) -> BuildingState:
        if self._state is None:
            self.initialize(self._config)
        assert self._state is not None
        if self._paused and n > 0:
            return deepcopy(self._state)
        for _ in range(n):
            self._state = self._advance(self._state)
        return deepcopy(self._state)

    def simulate_plan(
        self, state: BuildingState, plan: PlanInput, horizon: int
    ) -> SimulationResult:
        working = deepcopy(state)
        # Apply first actions as persistent setpoints for the horizon
        for action in plan.actions:
            if action.zone_id in working.zones:
                if action.action_type in {"cooling_setpoint", "request_zone_setpoint"}:
                    working.zones[action.zone_id].cooling_setpoint = action.value
                elif action.action_type == "heating_setpoint":
                    working.zones[action.zone_id].heating_setpoint = action.value

        trajectory: list[BuildingState] = []
        energy = 0.0
        cost = 0.0
        carbon = 0.0
        peak = working.total_building_power_kw
        comfort_viol_min = 0.0
        interval_h = self._config.interval_minutes / 60.0

        for _ in range(horizon):
            working = self._advance(working, mutate_faults=False)
            trajectory.append(deepcopy(working))
            energy += working.total_building_power_kw * interval_h
            cost += working.total_building_power_kw * interval_h * working.electricity_tariff
            carbon += working.total_building_power_kw * interval_h * (
                working.grid_carbon_intensity / 1000.0
            )
            peak = max(peak, working.total_building_power_kw)
            for zone in working.zones.values():
                if zone.occupancy_count > 0 and not (
                    zone.cooling_setpoint - 0.5 <= zone.temperature <= zone.cooling_setpoint + 1.0
                ):
                    comfort_viol_min += self._config.interval_minutes

        return SimulationResult(
            simulated=True,
            status="COMPLETED",
            horizon_steps=horizon,
            energy_kwh=round(energy, 2),
            cost=round(cost, 2),
            carbon_kg=round(carbon, 2),
            peak_kw=round(peak, 2),
            comfort_violation_minutes=float(comfort_viol_min),
            trajectory=trajectory,
            metrics={
                "label": "simulated",
                "provider": "mock",
                "plan_id": plan.plan_id,
            },
        )

    def _initial_state(self) -> BuildingState:
        zones: dict[str, ZoneState] = {}
        for zid, seed in ZONE_SEEDS.items():
            occ = int(seed["occupancy_count"])
            temp = float(seed["temperature"])
            cool = float(seed["cooling_setpoint"])
            hvac = max(2.5, abs(temp - cool) * 4.5 + occ * 0.08)
            zones[zid] = ZoneState(
                zone_id=zid,
                name=str(seed["name"]),
                temperature=temp,
                cooling_setpoint=cool,
                heating_setpoint=float(seed["heating_setpoint"]),
                relative_humidity=48.0 + (hash(zid) % 7),
                occupancy_count=occ,
                occupancy_probability=min(0.99, 0.35 + occ / 60.0),
                co2_ppm=520 + occ * 8,
                hvac_power_kw=round(hvac, 2),
                lighting_power_kw=round(1.2 + occ * 0.03, 2),
                plug_load_power_kw=round(1.5 + occ * 0.05, 2),
                airflow_m3_s=round(0.4 + occ * 0.01, 2),
                comfort_status=self._comfort(temp, cool, occ),
                sensor_health=float(seed["sensor_health"]),
                data_freshness_seconds=5.0,
                control_status="AUTO",
                predicted_temperature=temp,
            )
        total = sum(
            z.hvac_power_kw + z.lighting_power_kw + z.plug_load_power_kw for z in zones.values()
        )
        # Align to demo starting power ~112 kW with common area loads
        common = max(0.0, 112.0 - total)
        total += common
        return BuildingState(
            outdoor_temperature=self._config.initial_outdoor_temperature,
            outdoor_humidity=self._config.initial_outdoor_humidity,
            solar_radiation=780.0,
            electricity_tariff=self._config.initial_tariff,
            grid_carbon_intensity=self._config.initial_carbon_intensity,
            total_building_power_kw=round(total, 1),
            peak_demand_kw=round(total, 1),
            zones=zones,
            simulated=True,
            step_index=0,
            timestamp_iso=self._base_time.isoformat(),
        )

    def _advance(self, state: BuildingState, mutate_faults: bool = True) -> BuildingState:
        next_state = deepcopy(state)
        next_state.step_index += 1
        t = self._base_time + timedelta(minutes=self._config.interval_minutes * next_state.step_index)
        next_state.timestamp_iso = t.isoformat()
        hour = t.hour + t.minute / 60.0

        # Diurnal outdoor weather
        next_state.outdoor_temperature = (
            self._config.initial_outdoor_temperature
            + 2.5 * np.sin((hour - 14) / 24 * 2 * np.pi)
            + float(self._rng.normal(0, 0.15))
        )
        next_state.solar_radiation = max(0.0, 850 * max(0, np.sin((hour - 6) / 12 * np.pi)))
        next_state.grid_carbon_intensity = (
            self._config.initial_carbon_intensity
            + (120 if 17 <= hour <= 21 else 0)
            + float(self._rng.normal(0, 5))
        )
        next_state.electricity_tariff = self._config.initial_tariff + (
            2.5 if 12 <= hour <= 16 else 0.0
        )

        total = 18.0  # common loads
        for zid, zone in next_state.zones.items():
            outdoor_effect = 0.04 * (next_state.outdoor_temperature - zone.temperature)
            occ_effect = 0.01 * zone.occupancy_count
            solar_effect = 0.0008 * next_state.solar_radiation * (0.6 if zid == "core" else 1.0)
            cooling_error = zone.temperature - zone.cooling_setpoint
            hvac_effect = 0.35 * cooling_error
            noise = float(self._rng.normal(0, 0.05))
            new_temp = (
                zone.temperature
                + outdoor_effect
                + occ_effect
                + solar_effect
                - hvac_effect
                + noise
            )
            zone.predicted_temperature = round(new_temp, 2)

            if mutate_faults and zid in self._faults:
                fault = self._faults[zid]
                if fault["type"] == "temperature_spike":
                    zone.temperature = float(fault.get("value") or 55.0)
                    zone.sensor_health = 0.05
                    zone.sensor_failed = True
                    zone.estimated_temperature = round(new_temp, 2)
                    zone.comfort_status = "SENSOR_FAULT"
                elif fault["type"] == "offline":
                    zone.data_freshness_seconds += self._config.interval_minutes * 60
                    zone.sensor_health = 0.1
                    zone.comfort_status = "OFFLINE"
                    zone.estimated_temperature = round(new_temp, 2)
                else:
                    zone.temperature = round(new_temp, 2)
            else:
                zone.temperature = round(new_temp, 2)
                zone.data_freshness_seconds = 5.0 + float(self._rng.uniform(0, 10))
                if not zone.sensor_failed:
                    zone.sensor_health = max(0.5, min(0.99, zone.sensor_health + float(self._rng.normal(0, 0.005))))

            # Occupancy schedule shape
            if 8 <= hour < 19:
                base_occ = ZONE_SEEDS[zid]["occupancy_count"]
                zone.occupancy_probability = min(0.99, 0.55 + 0.3 * np.sin((hour - 8) / 11 * np.pi))
                if not (self._scenario == "occupancy_spike" and zid == "south"):
                    zone.occupancy_count = max(0, int(base_occ * zone.occupancy_probability / 0.75))
            else:
                zone.occupancy_count = max(0, int(ZONE_SEEDS[zid]["occupancy_count"] * 0.05))
                zone.occupancy_probability = 0.08

            zone.co2_ppm = round(480 + zone.occupancy_count * 9 + float(self._rng.normal(0, 8)), 0)
            zone.hvac_power_kw = round(
                max(1.5, abs(zone.temperature - zone.cooling_setpoint) * 5.0 + zone.occupancy_count * 0.09),
                2,
            )
            zone.lighting_power_kw = round(1.0 + zone.occupancy_count * 0.03, 2)
            zone.plug_load_power_kw = round(1.2 + zone.occupancy_count * 0.05, 2)
            zone.airflow_m3_s = round(0.35 + zone.occupancy_count * 0.012, 2)
            if not zone.sensor_failed and zone.comfort_status not in {"SENSOR_FAULT", "OFFLINE"}:
                zone.comfort_status = self._comfort(
                    zone.temperature, zone.cooling_setpoint, zone.occupancy_count
                )
            total += zone.hvac_power_kw + zone.lighting_power_kw + zone.plug_load_power_kw

        next_state.total_building_power_kw = round(total, 1)
        next_state.peak_demand_kw = max(next_state.peak_demand_kw, next_state.total_building_power_kw)
        return next_state

    @staticmethod
    def _comfort(temp: float, setpoint: float, occupancy: int) -> str:
        if occupancy <= 0:
            return "COMFORTABLE"
        delta = abs(temp - setpoint)
        if delta <= 0.6:
            return "COMFORTABLE"
        if delta <= 1.2:
            return "SLIGHTLY_UNCOMFORTABLE"
        return "UNCOMFORTABLE"
