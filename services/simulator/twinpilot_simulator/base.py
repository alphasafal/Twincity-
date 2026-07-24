"""Building simulator protocol and shared models."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ZoneState(BaseModel):
    zone_id: str
    name: str
    temperature: float
    cooling_setpoint: float
    heating_setpoint: float
    relative_humidity: float
    occupancy_count: int
    occupancy_probability: float
    co2_ppm: float
    hvac_power_kw: float
    lighting_power_kw: float
    plug_load_power_kw: float
    airflow_m3_s: float
    comfort_status: str
    sensor_health: float
    data_freshness_seconds: float
    control_status: str
    predicted_temperature: float | None = None
    estimated_temperature: float | None = None
    sensor_failed: bool = False


class BuildingState(BaseModel):
    outdoor_temperature: float
    outdoor_humidity: float
    solar_radiation: float
    electricity_tariff: float
    grid_carbon_intensity: float
    total_building_power_kw: float
    peak_demand_kw: float
    zones: dict[str, ZoneState]
    simulated: bool = True
    step_index: int = 0
    timestamp_iso: str = ""


class SimulationConfig(BaseModel):
    seed: int = 42
    interval_minutes: int = 15
    initial_outdoor_temperature: float = 34.0
    initial_outdoor_humidity: float = 58.0
    initial_carbon_intensity: float = 680.0
    initial_tariff: float = 9.5
    model_path: str | None = None
    weather_path: str | None = None
    energyplus_home: str | None = None


class ControlActionInput(BaseModel):
    zone_id: str
    action_type: str
    value: float
    duration_minutes: int = 60


class PlanInput(BaseModel):
    plan_id: str
    actions: list[ControlActionInput]
    horizon_steps: int = 16


class SimulationResult(BaseModel):
    simulated: bool = True
    status: str
    horizon_steps: int
    energy_kwh: float
    cost: float
    carbon_kg: float
    peak_kw: float
    comfort_violation_minutes: float
    trajectory: list[BuildingState] = Field(default_factory=list)
    error_message: str | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class BuildingSimulator(Protocol):
    def initialize(self, configuration: SimulationConfig) -> BuildingState: ...

    def get_state(self) -> BuildingState: ...

    def simulate_plan(
        self, state: BuildingState, plan: PlanInput, horizon: int
    ) -> SimulationResult: ...

    def apply_action(self, action: ControlActionInput) -> BuildingState: ...

    def reset(self) -> BuildingState: ...

    def health(self) -> dict[str, Any]: ...
