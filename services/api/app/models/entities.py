"""SQLAlchemy domain models."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base


def _uuid() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(64), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Building(Base):
    __tablename__ = "buildings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(200))
    location: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata")
    area_m2: Mapped[float] = mapped_column(Float, default=1560.0)
    building_type: Mapped[str] = mapped_column(String(64), default="commercial_office")
    current_mode: Mapped[str] = mapped_column(String(32), default="AUTONOMOUS", index=True)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confidence: Mapped[float] = mapped_column(Float, default=0.91)
    autonomy_confidence_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    zones: Mapped[list[Zone]] = relationship(back_populates="building")


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    floor: Mapped[int] = mapped_column(Integer, default=1)
    area_m2: Mapped[float] = mapped_column(Float)
    capacity: Mapped[int] = mapped_column(Integer)
    preferred_temperature: Mapped[float] = mapped_column(Float, default=23.5)
    minimum_temperature: Mapped[float] = mapped_column(Float, default=20.0)
    maximum_temperature: Mapped[float] = mapped_column(Float, default=27.0)
    external_key: Mapped[str] = mapped_column(String(64), index=True)

    building: Mapped[Building] = relationship(back_populates="zones")
    sensors: Mapped[list[Sensor]] = relationship(back_populates="zone")


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    zone_id: Mapped[str] = mapped_column(ForeignKey("zones.id"), index=True)
    sensor_type: Mapped[str] = mapped_column(String(64))
    external_identifier: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(32))
    health_status: Mapped[str] = mapped_column(String(32), default="HEALTHY")
    confidence: Mapped[float] = mapped_column(Float, default=0.95)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    zone: Mapped[Zone] = relationship(back_populates="sensors")


class TelemetryPoint(Base):
    __tablename__ = "telemetry_points"
    __table_args__ = (
        Index("ix_telemetry_building_ts", "building_id", "timestamp"),
        Index("ix_telemetry_zone_ts", "zone_id", "timestamp"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    building_id: Mapped[str] = mapped_column(String(36), index=True)
    zone_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    sensor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metric: Mapped[str] = mapped_column(String(64), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(32))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    quality: Mapped[str] = mapped_column(String(32), default="GOOD")
    source: Mapped[str] = mapped_column(String(64), default="mock_simulator")


class ComfortPolicy(Base):
    __tablename__ = "comfort_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), index=True)
    occupied_min_temperature: Mapped[float] = mapped_column(Float, default=21.0)
    occupied_max_temperature: Mapped[float] = mapped_column(Float, default=26.0)
    unoccupied_min_temperature: Mapped[float] = mapped_column(Float, default=18.0)
    unoccupied_max_temperature: Mapped[float] = mapped_column(Float, default=28.0)
    max_violation_minutes: Mapped[float] = mapped_column(Float, default=15.0)
    humidity_min: Mapped[float] = mapped_column(Float, default=30.0)
    humidity_max: Mapped[float] = mapped_column(Float, default=65.0)
    co2_max_ppm: Mapped[float] = mapped_column(Float, default=1000.0)


class GoalProfile(Base):
    __tablename__ = "goal_profiles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    energy_weight: Mapped[float] = mapped_column(Float, default=0.25)
    cost_weight: Mapped[float] = mapped_column(Float, default=0.20)
    carbon_weight: Mapped[float] = mapped_column(Float, default=0.20)
    comfort_weight: Mapped[float] = mapped_column(Float, default=0.20)
    peak_weight: Mapped[float] = mapped_column(Float, default=0.10)
    equipment_weight: Mapped[float] = mapped_column(Float, default=0.05)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ConstraintPolicy(Base):
    __tablename__ = "constraint_policies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    building_id: Mapped[str] = mapped_column(ForeignKey("buildings.id"), index=True)
    min_cooling_setpoint: Mapped[float] = mapped_column(Float, default=20.0)
    max_cooling_setpoint: Mapped[float] = mapped_column(Float, default=28.0)
    min_heating_setpoint: Mapped[float] = mapped_column(Float, default=16.0)
    max_heating_setpoint: Mapped[float] = mapped_column(Float, default=24.0)
    max_setpoint_change_per_interval: Mapped[float] = mapped_column(Float, default=1.5)
    minimum_ventilation: Mapped[float] = mapped_column(Float, default=0.3)
    maximum_control_duration: Mapped[int] = mapped_column(Integer, default=240)
    minimum_confidence_for_autonomy: Mapped[float] = mapped_column(Float, default=0.85)
    maximum_data_age_seconds: Mapped[int] = mapped_column(Integer, default=300)


class Forecast(Base):
    __tablename__ = "forecasts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    building_id: Mapped[str] = mapped_column(String(36), index=True)
    zone_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    forecast_type: Mapped[str] = mapped_column(String(64))
    horizon: Mapped[int] = mapped_column(Integer)
    values_json: Mapped[dict[str, Any]] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ControlPlan(Base):
    __tablename__ = "control_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    building_id: Mapped[str] = mapped_column(String(36), index=True)
    plan_name: Mapped[str] = mapped_column(String(160))
    source: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="CANDIDATE", index=True)
    objective_score: Mapped[float] = mapped_column(Float, default=0.0)
    predicted_metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    confidence: Mapped[float] = mapped_column(Float, default=0.8)
    feasibility: Mapped[bool] = mapped_column(Boolean, default=True)
    actions_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    score_breakdown_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    validation_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    validation_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    state_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ControlAction(Base):
    __tablename__ = "control_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    plan_id: Mapped[str] = mapped_column(ForeignKey("control_plans.id"), index=True)
    zone_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action_type: Mapped[str] = mapped_column(String(64))
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    proposed_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str] = mapped_column(String(32), default="°C")
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    risk_level: Mapped[str] = mapped_column(String(32), default="LOW")


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    building_id: Mapped[str] = mapped_column(String(36), index=True)
    plan_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    simulator_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    input_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    result_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class Decision(Base):
    __tablename__ = "decisions"
    __table_args__ = (Index("ix_decisions_building_created", "building_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    building_id: Mapped[str] = mapped_column(String(36), index=True)
    selected_plan_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    mode: Mapped[str] = mapped_column(String(32))
    trigger: Mapped[str] = mapped_column(String(120))
    explanation: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    validation_status: Mapped[str] = mapped_column(String(32), default="PENDING")
    execution_status: Mapped[str] = mapped_column(String(32), default="PENDING", index=True)
    predicted_metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    realized_metrics_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    prediction_error_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    candidate_plan_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    rejected_plan_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    observed_state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    goal_profile_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    applied_action_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    rollback_status: Mapped[str] = mapped_column(String(32), default="NONE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_building_severity", "building_id", "severity"),
        Index("ix_alerts_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    building_id: Mapped[str] = mapped_column(String(36), index=True)
    zone_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    decision_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    severity: Mapped[str] = mapped_column(String(32), index=True)
    alert_type: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(200))
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="OPEN")
    notes_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    assigned_to: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    acknowledged_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_building_ts", "building_id", "timestamp"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    building_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    event_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    previous_value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    new_value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    request_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class AssistantConversation(Base):
    __tablename__ = "assistant_conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), index=True)
    building_id: Mapped[str] = mapped_column(String(36), index=True)
    title: Mapped[str] = mapped_column(String(200), default="Operations chat")
    messages_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class PredictionLedgerEntry(Base):
    __tablename__ = "prediction_ledger"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    building_id: Mapped[str] = mapped_column(String(36), index=True)
    decision_id: Mapped[str] = mapped_column(String(36), index=True)
    plan_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    predicted_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    realized_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    error_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    confidence_before: Mapped[float] = mapped_column(Float, default=0.0)
    confidence_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    rollback_required: Mapped[bool] = mapped_column(Boolean, default=False)
    explanation: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
