"""Pydantic API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    name: str
    email: EmailStr
    role: str
    is_active: bool
    last_login_at: datetime | None = None

    model_config = {"from_attributes": True}


class BuildingOut(BaseModel):
    id: str
    name: str
    location: str
    timezone: str
    area_m2: float
    building_type: str
    current_mode: str
    is_demo: bool
    confidence: float
    autonomy_confidence_json: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class ModeUpdateRequest(BaseModel):
    mode: str
    reason: str = Field(min_length=3, max_length=500)


class ZoneOut(BaseModel):
    id: str
    building_id: str
    name: str
    floor: int
    area_m2: float
    capacity: int
    preferred_temperature: float
    minimum_temperature: float
    maximum_temperature: float
    external_key: str

    model_config = {"from_attributes": True}


class OverrideRequest(BaseModel):
    value: float
    duration_minutes: int = Field(ge=5, le=240)
    reason: str = Field(min_length=3, max_length=500)
    confirm: bool = False


class ApproveRejectRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class RollbackRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    target_safe_policy: str = "default_safe_policy"


class AlertNoteRequest(BaseModel):
    note: str = Field(min_length=1, max_length=1000)
    assign_to: str | None = None


class GoalWeightsRequest(BaseModel):
    energy_weight: float = 0.25
    cost_weight: float = 0.20
    carbon_weight: float = 0.20
    comfort_weight: float = 0.20
    peak_weight: float = 0.10
    equipment_weight: float = 0.05
    energy_target_pct: float | None = None
    zero_comfort_deviation: bool = False
    allow_schedule_changes: bool = True


class WhatIfRequest(BaseModel):
    outdoor_temperature: float | None = None
    occupancy_level: float | None = Field(default=None, ge=0, le=2)
    electricity_price: float | None = None
    grid_carbon_intensity: float | None = None
    comfort_band_width: float | None = None
    energy_saving_target: float | None = None
    time_horizon_steps: int = 16
    sensor_failures: list[str] = Field(default_factory=list)


class AssistantChatRequest(BaseModel):
    building_id: str
    message: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = None


class DemoSpeedRequest(BaseModel):
    speed: int


class TelemetryIngestRequest(BaseModel):
    building_id: str
    points: list[dict[str, Any]]


class BuildingUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    location: str | None = Field(default=None, min_length=2, max_length=200)
    timezone: str | None = Field(default=None, min_length=2, max_length=64)
    area_m2: float | None = Field(default=None, gt=0)
    building_type: str | None = Field(default=None, min_length=2, max_length=64)
    reason: str = Field(min_length=3, max_length=500)


class ConstraintUpdateRequest(BaseModel):
    min_cooling_setpoint: float | None = None
    max_cooling_setpoint: float | None = None
    min_heating_setpoint: float | None = None
    max_heating_setpoint: float | None = None
    max_setpoint_change_per_interval: float | None = Field(default=None, gt=0)
    minimum_ventilation: float | None = Field(default=None, ge=0, le=1)
    maximum_control_duration: int | None = Field(default=None, ge=5, le=1440)
    minimum_confidence_for_autonomy: float | None = Field(default=None, ge=0, le=1)
    maximum_data_age_seconds: int | None = Field(default=None, ge=30, le=3600)
    reason: str = Field(min_length=3, max_length=500)


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: str
    reason: str = Field(min_length=3, max_length=500)


class UserUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    role: str | None = None
    is_active: bool | None = None
    reason: str = Field(min_length=3, max_length=500)


class GoalUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    energy_weight: float | None = None
    cost_weight: float | None = None
    carbon_weight: float | None = None
    comfort_weight: float | None = None
    peak_weight: float | None = None
    equipment_weight: float | None = None
    reason: str = Field(min_length=3, max_length=500)
