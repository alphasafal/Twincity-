"""Versioned REST API routes."""

from __future__ import annotations

import csv
import io
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from twinpilot_agent import get_agent_provider
from twinpilot_optimizer.modes import OperatingMode
from twinpilot_optimizer.objective import ObjectiveWeights
from twinpilot_optimizer.planner import BuildingObservation, generate_candidate_plans
from twinpilot_optimizer.safety import (
    ConstraintLimits,
    ProposedAction,
    SafetyShield,
    ValidationContext,
    build_validation_token,
    parse_validation_token,
)
from twinpilot_simulator.base import ControlActionInput, PlanInput

from app.core.config import get_settings
from app.core.deps import (
    CurrentUser,
    DbSession,
    require_permission,
    require_roles,
)
from app.core.rate_limit import enforce_assistant_rate_limit, enforce_auth_rate_limit
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models import (
    Alert,
    AssistantConversation,
    AuditEvent,
    Building,
    ComfortPolicy,
    ConstraintPolicy,
    ControlPlan,
    Decision,
    GoalProfile,
    PredictionLedgerEntry,
    TelemetryPoint,
    User,
    Zone,
)
from app.models.enums import UserRole
from app.schemas.common import (
    AlertNoteRequest,
    ApproveRejectRequest,
    AssistantChatRequest,
    BuildingOut,
    BuildingUpdateRequest,
    ConstraintUpdateRequest,
    DemoSpeedRequest,
    GoalUpdateRequest,
    GoalWeightsRequest,
    LoginRequest,
    ModeUpdateRequest,
    OverrideRequest,
    RefreshRequest,
    RollbackRequest,
    TelemetryIngestRequest,
    TokenResponse,
    UserCreateRequest,
    UserOut,
    UserUpdateRequest,
    WhatIfRequest,
    ZoneOut,
)
from app.services.experiment_store import (
    experiment_dashboard_payload,
    load_actions,
    load_consolidated_scenarios,
    load_stream_frames,
    results_root,
)
from app.services.runtime import hub

router = APIRouter(prefix="/api/v1")
shield = SafetyShield()
settings = get_settings()


def _audit(
    db: Session,
    *,
    user_id: str | None,
    building_id: str | None,
    event_type: str,
    entity_type: str,
    entity_id: str | None,
    reason: str | None = None,
    previous: dict | None = None,
    new: dict | None = None,
    request_id: str | None = None,
) -> None:
    db.add(
        AuditEvent(
            user_id=user_id,
            building_id=building_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            previous_value_json=previous,
            new_value_json=new,
            reason=reason,
            request_id=request_id,
        )
    )


# ── Auth ──────────────────────────────────────────────────────────────
@router.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: DbSession, request: Request) -> TokenResponse:
    enforce_auth_rate_limit(request)
    user = db.scalar(select(User).where(User.email == payload.email))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    user.last_login_at = datetime.now(UTC)
    _audit(
        db,
        user_id=user.id,
        building_id=hub.building_id,
        event_type="login",
        entity_type="user",
        entity_id=user.id,
        request_id=getattr(request.state, "request_id", None),
    )
    db.commit()
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest, request: Request) -> TokenResponse:
    enforce_auth_rate_limit(request)
    try:
        data = decode_token(payload.refresh_token, refresh=True)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return TokenResponse(
        access_token=create_access_token(data["sub"]),
        refresh_token=create_refresh_token(data["sub"]),
    )


@router.post("/auth/logout")
def logout(user: CurrentUser) -> dict[str, str]:
    return {"status": "logged_out", "user_id": user.id}


@router.get("/auth/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


# ── Buildings ─────────────────────────────────────────────────────────
@router.get("/buildings", response_model=list[BuildingOut])
def list_buildings(db: DbSession, user: CurrentUser) -> list[Building]:
    return list(db.scalars(select(Building)).all())


@router.get("/buildings/{building_id}", response_model=BuildingOut)
def get_building(building_id: str, db: DbSession, user: CurrentUser) -> Building:
    building = db.get(Building, building_id)
    if not building:
        raise HTTPException(404, "Building not found")
    return building


@router.patch("/buildings/{building_id}/mode", response_model=BuildingOut)
def patch_mode(
    building_id: str,
    payload: ModeUpdateRequest,
    db: DbSession,
    user: User = Depends(require_permission("mode_change")),
) -> Building:
    building = db.get(Building, building_id)
    if not building:
        raise HTTPException(404, "Building not found")
    prev = building.current_mode
    building.current_mode = OperatingMode(payload.mode).value
    _audit(
        db,
        user_id=user.id,
        building_id=building_id,
        event_type="mode_changed",
        entity_type="building",
        entity_id=building_id,
        reason=payload.reason,
        previous={"mode": prev},
        new={"mode": building.current_mode},
    )
    db.commit()
    db.refresh(building)
    return building


@router.get("/buildings/{building_id}/status")
def building_status(building_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    building = db.get(Building, building_id)
    if not building:
        raise HTTPException(404, "Building not found")
    open_alerts = db.query(Alert).filter(Alert.building_id == building_id, Alert.status != "RESOLVED").count()
    pending = (
        db.query(Decision)
        .filter(Decision.building_id == building_id, Decision.execution_status == "PENDING")
        .count()
    )
    state = hub.latest_state or {}
    cfg = get_settings()
    data_mode = (cfg.data_mode or "energyplus").strip().lower()
    if cfg.hackathon_mode and data_mode not in {"energyplus", "mock"}:
        data_mode = "energyplus"

    experiment = experiment_dashboard_payload(cfg.experiment_scenario)
    if data_mode == "energyplus" and experiment.get("available"):
        reductions = experiment["reductions"]
        agent = experiment["agent"]
        baseline = experiment["baseline"]
        energy_saved_pct = reductions.get("total_energy_pct") or 0.0
        peak_reduction = reductions.get("peak_power_pct") or 0.0
        carbon_avoided = round(
            float(baseline["carbon_estimate_kg"]) - float(agent["carbon_estimate_kg"]), 2
        )
        # Comfort compliance from measured violation hours over proxy occupied hours (~28)
        occ_hours = 28.0
        comfort_pct = round(
            100.0
            * max(0.0, occ_hours - float(agent["occupied_comfort_violation_hours"]))
            / occ_hours,
            1,
        )
        return {
            "building": BuildingOut.model_validate(building).model_dump(),
            "mode": building.current_mode,
            "confidence": building.autonomy_confidence_json,
            "live_total_load_kw": agent["peak_power_kw"],
            "energy_saved_today_pct": round(float(energy_saved_pct), 2),
            "cost_saved_today": None,
            "carbon_avoided_today_kg": carbon_avoided,
            "peak_demand_reduction_pct": round(float(peak_reduction), 2),
            "comfort_compliance_pct": comfort_pct,
            "healthy_sensors_pct": 100.0,
            "active_alerts": open_alerts,
            "pending_decisions": pending,
            "state": state,
            "service_health": hub.service_health,
            "kpi_history": hub.kpi_history[-96:],
            "simulated": False,
            "data_mode": "energyplus",
            "data_label": "energyplus_experiment_results",
            "data_source_visible": "EnergyPlus experiment results (results/*)",
            "synthetic_multiplier_applied": False,
            "experiment": experiment,
            "simulator_health": hub.simulator.health(),
            "active_scenario": hub.active_scenario or cfg.experiment_scenario,
        }

    # EnergyPlus mode without usable artifacts must NOT silently become mock.
    if data_mode == "energyplus":
        return {
            "building": BuildingOut.model_validate(building).model_dump(),
            "mode": building.current_mode,
            "confidence": building.autonomy_confidence_json,
            "live_total_load_kw": None,
            "energy_saved_today_pct": None,
            "cost_saved_today": None,
            "carbon_avoided_today_kg": None,
            "peak_demand_reduction_pct": None,
            "comfort_compliance_pct": None,
            "healthy_sensors_pct": None,
            "active_alerts": open_alerts,
            "pending_decisions": pending,
            "state": state,
            "service_health": hub.service_health,
            "kpi_history": hub.kpi_history[-96:],
            "simulated": False,
            "data_mode": "energyplus",
            "data_label": "energyplus_results_unavailable",
            "data_source_visible": (
                "No EnergyPlus experiment results found. "
                "Run the baseline and agent experiment scripts first."
            ),
            "synthetic_multiplier_applied": False,
            "experiment": experiment,
            "experiment_available": False,
            "missing_artifacts": experiment.get("missing_artifacts") or [],
            "simulator_health": hub.simulator.health(),
            "active_scenario": hub.active_scenario or cfg.experiment_scenario,
            "note": (
                "No EnergyPlus experiment results found. "
                "Run the baseline and agent experiment scripts first. "
                "DATA_MODE=energyplus will not switch to mock automatically; "
                "set DATA_MODE=mock explicitly for mock development mode."
            ),
        }

    # Explicit mock mode only — no synthetic x1.12 savings
    return {
        "building": BuildingOut.model_validate(building).model_dump(),
        "mode": building.current_mode,
        "confidence": building.autonomy_confidence_json,
        "live_total_load_kw": state.get("total_building_power_kw"),
        "energy_saved_today_pct": 0.0,
        "cost_saved_today": 0.0,
        "carbon_avoided_today_kg": 0.0,
        "peak_demand_reduction_pct": 0.0,
        "comfort_compliance_pct": hub.comfort_compliance,
        "healthy_sensors_pct": round(
            100
            * sum(1 for z in state.get("zones", {}).values() if z.get("sensor_health", 0) >= 0.8)
            / max(1, len(state.get("zones", {}))),
            1,
        ),
        "active_alerts": open_alerts,
        "pending_decisions": pending,
        "state": state,
        "service_health": hub.service_health,
        "kpi_history": hub.kpi_history[-96:],
        "simulated": True,
        "data_mode": "mock",
        "data_label": "mock_twin",
        "data_source_visible": "Mock digital twin (no EnergyPlus meters)",
        "synthetic_multiplier_applied": False,
        "experiment": experiment if experiment.get("available") else None,
        "simulator_health": hub.simulator.health(),
        "active_scenario": hub.active_scenario,
        "note": (
            "Mock mode does not invent savings. Set DATA_MODE=energyplus for "
            "measured baseline-vs-agent KPIs."
        ),
    }


# ── Zones ─────────────────────────────────────────────────────────────
@router.get("/buildings/{building_id}/zones", response_model=list[ZoneOut])
def list_zones(building_id: str, db: DbSession, user: CurrentUser) -> list[Zone]:
    return list(db.scalars(select(Zone).where(Zone.building_id == building_id)).all())


@router.get("/zones/{zone_id}", response_model=ZoneOut)
def get_zone(zone_id: str, db: DbSession, user: CurrentUser) -> Zone:
    zone = db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(404, "Zone not found")
    return zone


@router.get("/zones/{zone_id}/telemetry")
def zone_telemetry(
    zone_id: str,
    db: DbSession,
    user: CurrentUser,
    limit: int = Query(default=100, le=1000),
) -> list[dict[str, Any]]:
    rows = (
        db.query(TelemetryPoint)
        .filter(TelemetryPoint.zone_id == zone_id)
        .order_by(TelemetryPoint.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "metric": r.metric,
            "value": r.value,
            "unit": r.unit,
            "timestamp": r.timestamp.isoformat(),
            "quality": r.quality,
        }
        for r in rows
    ]


@router.get("/zones/{zone_id}/health")
def zone_health(zone_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    zone = db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(404, "Zone not found")
    key = zone.external_key
    live = (hub.latest_state.get("zones") or {}).get(key, {})
    return {
        "zone_id": zone_id,
        "name": zone.name,
        "sensor_health": live.get("sensor_health"),
        "sensor_failed": live.get("sensor_failed"),
        "data_freshness_seconds": live.get("data_freshness_seconds"),
        "comfort_status": live.get("comfort_status"),
        "estimated_temperature": live.get("estimated_temperature"),
        "live": live,
    }


@router.post("/zones/{zone_id}/override")
def zone_override(
    zone_id: str,
    payload: OverrideRequest,
    db: DbSession,
    user: User = Depends(require_permission("manual_override")),
) -> dict[str, Any]:
    if not payload.confirm:
        raise HTTPException(400, "Confirmation required")
    zone = db.get(Zone, zone_id)
    if not zone:
        raise HTTPException(404, "Zone not found")
    key = zone.external_key
    current = float((hub.latest_state.get("zones") or {}).get(key, {}).get("cooling_setpoint", 24))
    constraints = (
        db.query(ConstraintPolicy).filter(ConstraintPolicy.building_id == zone.building_id).first()
    )
    building = db.get(Building, zone.building_id)
    context = ValidationContext(
        mode=OperatingMode(building.current_mode if building else "MANUAL"),
        confidence=building.confidence if building else 0.5,
        data_age_seconds=10,
        required_sensors_healthy=True,
        simulation_ok=True,
        state_snapshot_matches=True,
        user_has_permission=True,
        approval_required=False,
        approved=True,
        limits=ConstraintLimits(
            min_cooling_setpoint=constraints.min_cooling_setpoint if constraints else 20,
            max_cooling_setpoint=constraints.max_cooling_setpoint if constraints else 28,
            max_setpoint_change_per_interval=(
                constraints.max_setpoint_change_per_interval if constraints else 1.5
            ),
        ),
    )
    result = shield.validate(
        ProposedAction(
            action_type="cooling_setpoint",
            zone_id=key,
            current_value=current,
            proposed_value=payload.value,
            duration_minutes=payload.duration_minutes,
        ),
        context,
    )
    if not result.valid:
        raise HTTPException(400, {"message": "Safety Shield rejected override", "result": result.model_dump()})
    hub.simulator.apply_action(
        ControlActionInput(
            zone_id=key,
            action_type="cooling_setpoint",
            value=payload.value,
            duration_minutes=payload.duration_minutes,
        )
    )
    _audit(
        db,
        user_id=user.id,
        building_id=zone.building_id,
        event_type="manual_override",
        entity_type="zone",
        entity_id=zone_id,
        reason=payload.reason,
        previous={"cooling_setpoint": current},
        new={"cooling_setpoint": payload.value, "duration_minutes": payload.duration_minutes},
    )
    db.commit()
    hub.latest_state = hub.simulator.get_state().model_dump()
    return {"status": "applied", "safety": result.model_dump(), "state": hub.latest_state["zones"][key]}


# ── Telemetry ─────────────────────────────────────────────────────────
@router.get("/buildings/{building_id}/telemetry/latest")
def telemetry_latest(building_id: str, user: CurrentUser) -> dict[str, Any]:
    return {
        "building_id": building_id,
        "state": hub.latest_state,
        "simulated": bool((hub.latest_state or {}).get("simulated", True)),
        "data_label": "mock_twin"
        if (hub.latest_state or {}).get("simulated", True)
        else "energyplus_or_measured",
    }


@router.get("/buildings/{building_id}/telemetry/history")
def telemetry_history(
    building_id: str,
    db: DbSession,
    user: CurrentUser,
    metric: str = "total_building_power_kw",
    limit: int = 200,
) -> list[dict[str, Any]]:
    rows = (
        db.query(TelemetryPoint)
        .filter(TelemetryPoint.building_id == building_id, TelemetryPoint.metric == metric)
        .order_by(TelemetryPoint.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        {"timestamp": r.timestamp.isoformat(), "value": r.value, "unit": r.unit, "quality": r.quality}
        for r in reversed(rows)
    ]


@router.post("/telemetry/ingest")
def telemetry_ingest(
    payload: TelemetryIngestRequest,
    request: Request,
    db: DbSession,
) -> dict[str, Any]:
    token = request.headers.get("x-telemetry-token")
    if not settings.demo_mode and token != settings.telemetry_ingest_token:
        raise HTTPException(401, "Invalid telemetry ingest token")
    count = 0
    for point in payload.points[:500]:
        db.add(
            TelemetryPoint(
                building_id=payload.building_id,
                zone_id=point.get("zone_id"),
                sensor_id=point.get("sensor_id"),
                metric=str(point.get("metric", "unknown"))[:64],
                value=float(point.get("value", 0)),
                unit=str(point.get("unit", "")),
                timestamp=datetime.now(UTC),
                quality=str(point.get("quality", "GOOD")),
                source=str(point.get("source", "ingest")),
            )
        )
        count += 1
    db.commit()
    return {"ingested": count}


# ── Optimization / plans ──────────────────────────────────────────────
@router.post("/buildings/{building_id}/optimization/generate")
def generate_optimization(
    building_id: str,
    payload: GoalWeightsRequest,
    db: DbSession,
    user: CurrentUser,
) -> dict[str, Any]:
    building = db.get(Building, building_id)
    if not building:
        raise HTTPException(404, "Building not found")
    weights = ObjectiveWeights(
        energy_weight=payload.energy_weight,
        cost_weight=payload.cost_weight,
        carbon_weight=payload.carbon_weight,
        comfort_weight=payload.comfort_weight,
        peak_weight=payload.peak_weight,
        equipment_weight=payload.equipment_weight,
    )
    state = hub.latest_state
    obs = hub._to_observation(state)
    if hub.active_scenario == "infeasible_target" or (
        payload.energy_target_pct and payload.energy_target_pct >= 40 and payload.zero_comfort_deviation
    ):
        plans = generate_candidate_plans(
            obs,
            weights,
            energy_target_pct=payload.energy_target_pct or 40,
            allow_schedule_changes=payload.allow_schedule_changes,
            zero_comfort_deviation=True,
        )
    else:
        plans = generate_candidate_plans(
            obs,
            weights,
            energy_target_pct=payload.energy_target_pct,
            allow_schedule_changes=payload.allow_schedule_changes,
            zero_comfort_deviation=payload.zero_comfort_deviation,
        )
    state_hash = hub._state_hash(state)
    saved = []
    for plan in plans:
        row = ControlPlan(
            building_id=building_id,
            plan_name=plan.plan_name,
            source=plan.source.value,
            status="CANDIDATE",
            objective_score=plan.score.utility,
            predicted_metrics_json=plan.metrics.model_dump(),
            confidence=plan.confidence,
            feasibility=plan.metrics.feasible,
            actions_json=[a.model_dump() for a in plan.actions],
            score_breakdown_json=plan.score.model_dump(),
            state_hash=state_hash,
            expires_at=datetime.now(UTC).replace(microsecond=0)
            + __import__("datetime").timedelta(minutes=30),
        )
        db.add(row)
        db.flush()
        saved.append(
            {
                "id": row.id,
                "plan_name": row.plan_name,
                "source": row.source,
                "status": row.status,
                "objective_score": row.objective_score,
                "predicted_metrics_json": row.predicted_metrics_json,
                "confidence": row.confidence,
                "feasibility": row.feasibility,
                "actions_json": row.actions_json,
                "score_breakdown_json": row.score_breakdown_json,
                "simulation_status": "PENDING",
            }
        )
    db.commit()
    return {
        "plans": saved,
        "weights": weights.model_dump(),
        "simulated": bool((hub.latest_state or {}).get("simulated", True)),
    }


@router.get("/control-plans/{plan_id}")
def get_plan(plan_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    plan = db.get(ControlPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    return {
        "id": plan.id,
        "plan_name": plan.plan_name,
        "source": plan.source,
        "status": plan.status,
        "objective_score": plan.objective_score,
        "predicted_metrics_json": plan.predicted_metrics_json,
        "confidence": plan.confidence,
        "feasibility": plan.feasibility,
        "actions_json": plan.actions_json,
        "score_breakdown_json": plan.score_breakdown_json,
        "validation_json": plan.validation_json,
        "validation_token": plan.validation_token,
        "expires_at": plan.expires_at.isoformat() if plan.expires_at else None,
        "state_hash": plan.state_hash,
    }


def _validate_plan_row(db: Session, plan: ControlPlan, building: Building, *, approved: bool = False) -> dict:
    now = datetime.now(UTC)
    expires_at = plan.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        # SQLite often returns naive datetimes; treat as UTC
        expires_at = expires_at.replace(tzinfo=UTC)
    if expires_at and expires_at < now:
        plan.status = "EXPIRED"
        result = {
            "valid": False,
            "risk_level": "HIGH",
            "checks": [{"name": "plan_expiry", "passed": False, "message": "Plan has expired"}],
            "blocking_reasons": ["The plan has expired"],
        }
        plan.validation_json = result
        return result
    action = (plan.actions_json or [None])[0]
    if not action:
        raise HTTPException(400, "Plan has no actions")

    # Reject plans only when the proposed move is no longer coherent with live
    # setpoints (e.g. another control already moved past the proposal).
    live_zones = hub.latest_state.get("zones") or {}
    baseline_ok = True
    for act in plan.actions_json or []:
        z = live_zones.get(act.get("zone_id") or "")
        if not z:
            baseline_ok = False
            break
        live_sp = float(z.get("cooling_setpoint", 0))
        proposed = float(act.get("proposed_value", live_sp))
        # Refresh stored baseline to the live actuator value for revalidation.
        act["current_value"] = live_sp
        if abs(proposed - live_sp) > 1.5 + 1e-9:
            baseline_ok = False
            break
    plan.actions_json = list(plan.actions_json or [])
    current_hash = hub._state_hash(hub.latest_state)
    state_ok = baseline_ok

    constraints = (
        db.query(ConstraintPolicy).filter(ConstraintPolicy.building_id == building.id).first()
    )
    comfort_minutes = float(
        (plan.predicted_metrics_json or {}).get("comfort_violation_minutes", 0)
    )
    context = ValidationContext(
        mode=OperatingMode(building.current_mode),
        confidence=building.confidence,
        data_age_seconds=max(
            z.get("data_freshness_seconds", 0) for z in live_zones.values()
        )
        if live_zones
        else 0,
        required_sensors_healthy=all(not z.get("sensor_failed") for z in live_zones.values()),
        simulated_comfort_violation_minutes=comfort_minutes,
        critical_alert_blocking=building.current_mode == "FALLBACK",
        simulation_ok=not hub.force_simulation_failure and plan.status in {
            "SIMULATED",
            "VALIDATED",
            "APPROVED",
            "CANDIDATE",
            "APPLIED",
            "REJECTED",  # may be approval-gated; other checks still apply
        },
        state_snapshot_matches=state_ok,
        plan_expired=False,
        approval_required=building.current_mode in {"ADVISORY", "MANUAL"},
        approved=approved,
        user_has_permission=True,
        limits=ConstraintLimits(
            min_cooling_setpoint=constraints.min_cooling_setpoint if constraints else 20,
            max_cooling_setpoint=constraints.max_cooling_setpoint if constraints else 28,
            max_setpoint_change_per_interval=(
                constraints.max_setpoint_change_per_interval if constraints else 1.5
            ),
        ),
    )
    # Prefer the live snapshot hash inside the token so apply revalidation is bound
    # to current telemetry while still requiring a fresh Safety Shield pass.
    plan.state_hash = current_hash
    token = build_validation_token(plan.id, plan.state_hash or "", "api")
    safety = shield.validate(
        ProposedAction(
            action_type=action["action_type"],
            zone_id=action.get("zone_id"),
            current_value=float(
                live_zones.get(action.get("zone_id") or "", {}).get(
                    "cooling_setpoint", action.get("current_value") or 0
                )
            ),
            proposed_value=action.get("proposed_value"),
            duration_minutes=action.get("duration_minutes", 60),
        ),
        context,
        validation_token=token,
    )
    plan.validation_json = safety.model_dump()
    plan.validation_token = safety.validation_token
    if safety.valid:
        plan.status = "VALIDATED"
    else:
        # Keep SIMULATED/CANDIDATE when the only blocker is missing advisory
        # approval so a subsequent approve+revalidate can still succeed.
        approval_only = set(safety.blocking_reasons) <= {
            "Operator approval is required in ADVISORY mode",
            "Action is not allowed in MANUAL mode",
        }
        if not approval_only:
            plan.status = "REJECTED"
    return safety.model_dump()


@router.post("/control-plans/{plan_id}/simulate")
def simulate_plan(
    plan_id: str,
    db: DbSession,
    user: User = Depends(require_permission("simulation_run")),
) -> dict[str, Any]:
    plan = db.get(ControlPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    if hub.force_simulation_failure:
        plan.status = "CANDIDATE"
        db.commit()
        raise HTTPException(503, "Simulation service failure")
    # Bind simulation to the current building snapshot so validation can proceed
    # without accepting plans simulated against stale telemetry.
    hub.latest_state = hub.simulator.get_state().model_dump()
    live_zones = hub.latest_state.get("zones") or {}
    refreshed_actions = []
    for act in plan.actions_json or []:
        updated = dict(act)
        z = live_zones.get(act.get("zone_id") or "")
        if z is not None:
            updated["current_value"] = float(z.get("cooling_setpoint", act.get("current_value")))
        refreshed_actions.append(updated)
    plan.actions_json = refreshed_actions
    plan_input = PlanInput(
        plan_id=plan.id,
        actions=[
            ControlActionInput(
                zone_id=a["zone_id"],
                action_type=a["action_type"],
                value=float(a["proposed_value"]),
                duration_minutes=int(a.get("duration_minutes", 60)),
            )
            for a in refreshed_actions
        ],
    )
    plan.state_hash = hub._state_hash(hub.latest_state)
    result = hub.simulator.simulate_plan(hub.simulator.get_state(), plan_input, horizon=16)
    plan.status = "SIMULATED"
    prior = plan.predicted_metrics_json or {}
    plan.predicted_metrics_json = {
        **prior,
        "simulated_energy_kwh": result.energy_kwh,
        "simulated_cost": result.cost,
        "simulated_carbon_kg": result.carbon_kg,
        "simulated_peak_kw": result.peak_kw,
        "comfort_violation_minutes": float(result.comfort_violation_minutes),
        "planner_comfort_violation_minutes": prior.get("comfort_violation_minutes", 0),
        "label": "mock_twin_simulated"
        if result.simulated
        else result.metrics.get("label", "energyplus_anchored"),
        "simulated": result.simulated,
    }
    db.commit()
    return {"status": "COMPLETED", "result": result.model_dump(), "plan_id": plan.id}


@router.post("/control-plans/{plan_id}/validate")
def validate_plan(plan_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    plan = db.get(ControlPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    building = db.get(Building, plan.building_id)
    if not building:
        raise HTTPException(404, "Building not found")
    result = _validate_plan_row(db, plan, building, approved=False)
    db.commit()
    return result


@router.post("/control-plans/{plan_id}/approve")
def approve_plan(
    plan_id: str,
    payload: ApproveRejectRequest,
    db: DbSession,
    user: User = Depends(require_permission("plan_approve_low")),
) -> dict[str, Any]:
    plan = db.get(ControlPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    building = db.get(Building, plan.building_id)
    if not building:
        raise HTTPException(404, "Building not found")
    # High-risk requires elevated permission
    risk = ((plan.validation_json or {}).get("risk_level") or "LOW").upper()
    if risk in {"HIGH", "CRITICAL"} and user.role not in {
        UserRole.ADMINISTRATOR.value,
        UserRole.FACILITY_MANAGER.value,
    }:
        raise HTTPException(403, "High-risk approval requires facility manager or administrator")
    result = _validate_plan_row(db, plan, building, approved=True)
    if not result.get("valid"):
        raise HTTPException(400, {"message": "Approval cannot bypass constraints", "result": result})
    plan.status = "APPROVED"
    _audit(
        db,
        user_id=user.id,
        building_id=plan.building_id,
        event_type="plan_approved",
        entity_type="control_plan",
        entity_id=plan.id,
        reason=payload.reason,
        new={"status": "APPROVED"},
    )
    db.commit()
    return {"status": "APPROVED", "validation": result}


@router.post("/control-plans/{plan_id}/reject")
def reject_plan(
    plan_id: str,
    payload: ApproveRejectRequest,
    db: DbSession,
    user: CurrentUser,
) -> dict[str, Any]:
    plan = db.get(ControlPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    plan.status = "REJECTED"
    _audit(
        db,
        user_id=user.id,
        building_id=plan.building_id,
        event_type="plan_rejected",
        entity_type="control_plan",
        entity_id=plan.id,
        reason=payload.reason,
    )
    decision = (
        db.query(Decision)
        .filter(Decision.selected_plan_id == plan.id)
        .order_by(Decision.created_at.desc())
        .first()
    )
    if decision:
        decision.execution_status = "REJECTED"
        decision.explanation = (decision.explanation or "") + f" Rejected: {payload.reason}"
    db.commit()
    return {"status": "REJECTED"}


@router.post("/control-plans/{plan_id}/apply")
def apply_plan(
    plan_id: str,
    db: DbSession,
    user: User = Depends(require_permission("plan_execute")),
) -> dict[str, Any]:
    plan = db.get(ControlPlan, plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
    building = db.get(Building, plan.building_id)
    if not building:
        raise HTTPException(404, "Building not found")
    # Independently re-run validation
    approved = plan.status == "APPROVED" or building.current_mode in {"AUTONOMOUS", "GUARDED"}
    result = _validate_plan_row(db, plan, building, approved=approved)
    if not result.get("valid"):
        raise HTTPException(400, {"message": "Safety Shield rejected apply", "result": result})
    if not plan.validation_token:
        raise HTTPException(400, "Missing validation token")
    try:
        parse_validation_token(plan.validation_token)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    action = plan.actions_json[0]
    hub.simulator.apply_action(
        ControlActionInput(
            zone_id=action["zone_id"],
            action_type=action["action_type"],
            value=float(action["proposed_value"]),
            duration_minutes=int(action.get("duration_minutes", 60)),
        )
    )
    plan.status = "APPLIED"
    decision = Decision(
        building_id=plan.building_id,
        selected_plan_id=plan.id,
        mode=building.current_mode,
        trigger="operator_apply",
        explanation="Action approved by the Safety Shield.",
        confidence=building.confidence,
        validation_status="PASSED",
        execution_status="APPLIED",
        predicted_metrics_json=plan.predicted_metrics_json,
        applied_action_json=action,
        executed_at=datetime.now(UTC),
        observed_state_json={"power": hub.latest_state.get("total_building_power_kw")},
        goal_profile_json=plan.score_breakdown_json,
    )
    db.add(decision)
    db.flush()
    db.add(
        PredictionLedgerEntry(
            building_id=plan.building_id,
            decision_id=decision.id,
            plan_id=plan.id,
            predicted_json=plan.predicted_metrics_json,
            confidence_before=building.confidence,
            explanation="Applied after independent revalidation",
        )
    )
    _audit(
        db,
        user_id=user.id,
        building_id=plan.building_id,
        event_type="control_applied",
        entity_type="control_plan",
        entity_id=plan.id,
        reason="Operator/system apply after Safety Shield approval",
        new=action,
    )
    db.commit()
    hub.latest_state = hub.simulator.get_state().model_dump()
    return {"status": "APPLIED", "decision_id": decision.id, "validation": result}


# ── Rollback ──────────────────────────────────────────────────────────
@router.post("/buildings/{building_id}/rollback")
def rollback(
    building_id: str,
    payload: RollbackRequest,
    db: DbSession,
    user: User = Depends(require_permission("rollback")),
) -> dict[str, Any]:
    result = hub.rollback_to_safe_policy(
        db, building_id, reason=payload.reason, user_id=user.id
    )
    db.commit()
    return result


# ── Decisions / alerts / analytics ────────────────────────────────────
@router.get("/buildings/{building_id}/decisions")
def list_decisions(
    building_id: str,
    db: DbSession,
    user: CurrentUser,
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[dict[str, Any]]:
    q = db.query(Decision).filter(Decision.building_id == building_id)
    if status_filter:
        q = q.filter(Decision.execution_status == status_filter)
    rows = q.order_by(Decision.created_at.desc()).limit(100).all()
    return [
        {
            "id": d.id,
            "mode": d.mode,
            "trigger": d.trigger,
            "explanation": d.explanation,
            "confidence": d.confidence,
            "validation_status": d.validation_status,
            "execution_status": d.execution_status,
            "predicted_metrics_json": d.predicted_metrics_json,
            "realized_metrics_json": d.realized_metrics_json,
            "prediction_error_json": d.prediction_error_json,
            "rollback_status": d.rollback_status,
            "selected_plan_id": d.selected_plan_id,
            "applied_action_json": d.applied_action_json,
            "created_at": d.created_at.isoformat() if d.created_at else None,
            "executed_at": d.executed_at.isoformat() if d.executed_at else None,
        }
        for d in rows
    ]


@router.get("/decisions/{decision_id}")
def get_decision(decision_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    d = db.get(Decision, decision_id)
    if not d:
        raise HTTPException(404, "Decision not found")
    return {
        "id": d.id,
        "building_id": d.building_id,
        "selected_plan_id": d.selected_plan_id,
        "mode": d.mode,
        "trigger": d.trigger,
        "explanation": d.explanation,
        "confidence": d.confidence,
        "validation_status": d.validation_status,
        "execution_status": d.execution_status,
        "predicted_metrics_json": d.predicted_metrics_json,
        "realized_metrics_json": d.realized_metrics_json,
        "prediction_error_json": d.prediction_error_json,
        "candidate_plan_ids_json": d.candidate_plan_ids_json,
        "rejected_plan_ids_json": d.rejected_plan_ids_json,
        "observed_state_json": d.observed_state_json,
        "goal_profile_json": d.goal_profile_json,
        "applied_action_json": d.applied_action_json,
        "rollback_status": d.rollback_status,
        "created_at": d.created_at.isoformat() if d.created_at else None,
        "executed_at": d.executed_at.isoformat() if d.executed_at else None,
    }


@router.get("/decisions/{decision_id}/explanation")
async def explain_decision(decision_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    d = db.get(Decision, decision_id)
    if not d:
        raise HTTPException(404, "Decision not found")
    building = db.get(Building, d.building_id)
    agent = get_agent_provider(
        settings.agent_provider,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
    )
    out = await agent.explain(
        {
            "question": "Why was this decision made?",
            "decision": {
                "selected_plan_id": d.selected_plan_id,
                "explanation": d.explanation,
                "validation_status": d.validation_status,
                "applied_action_json": d.applied_action_json,
            },
            "mode": building.current_mode if building else "ADVISORY",
        }
    )
    return out.model_dump()


@router.get("/buildings/{building_id}/alerts")
def list_alerts(building_id: str, db: DbSession, user: CurrentUser) -> list[dict[str, Any]]:
    rows = (
        db.query(Alert)
        .filter(Alert.building_id == building_id)
        .order_by(Alert.created_at.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": a.id,
            "zone_id": a.zone_id,
            "decision_id": a.decision_id,
            "severity": a.severity,
            "alert_type": a.alert_type,
            "title": a.title,
            "message": a.message,
            "status": a.status,
            "notes_json": a.notes_json,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in rows
    ]


@router.patch("/alerts/{alert_id}/acknowledge")
def ack_alert(alert_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = "ACKNOWLEDGED"
    alert.acknowledged_by = user.id
    alert.acknowledged_at = datetime.now(UTC)
    db.commit()
    return {"status": "ACKNOWLEDGED"}


@router.patch("/alerts/{alert_id}/resolve")
def resolve_alert(alert_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = "RESOLVED"
    alert.resolved_at = datetime.now(UTC)
    db.commit()
    return {"status": "RESOLVED"}


@router.post("/alerts/{alert_id}/notes")
def alert_notes(alert_id: str, payload: AlertNoteRequest, db: DbSession, user: CurrentUser) -> dict:
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    notes = list(alert.notes_json or [])
    notes.append(
        {
            "note": payload.note,
            "by": user.id,
            "at": datetime.now(UTC).isoformat(),
        }
    )
    alert.notes_json = notes
    if payload.assign_to:
        alert.assigned_to = payload.assign_to
    db.commit()
    return {"status": "ok", "notes": notes}


@router.get("/buildings/{building_id}/analytics/summary")
def analytics_summary(building_id: str, user: CurrentUser) -> dict[str, Any]:
    cfg = get_settings()
    data_mode = (cfg.data_mode or "energyplus").strip().lower()
    experiment = experiment_dashboard_payload(cfg.experiment_scenario)
    if data_mode == "energyplus" and experiment.get("available"):
        return {
            "building_id": building_id,
            "data_mode": "energyplus",
            "energy_usage_kwh": experiment["agent"]["total_energy_kwh"],
            "baseline_energy_kwh": experiment["baseline"]["total_energy_kwh"],
            "estimated_savings_pct": experiment["reductions"]["total_energy_pct"],
            "hvac_energy_kwh": experiment["agent"]["hvac_energy_kwh"],
            "baseline_hvac_energy_kwh": experiment["baseline"]["hvac_energy_kwh"],
            "hvac_savings_pct": experiment["reductions"]["hvac_energy_pct"],
            "cost_saved": None,
            "carbon_avoided_kg": round(
                experiment["baseline"]["carbon_estimate_kg"]
                - experiment["agent"]["carbon_estimate_kg"],
                2,
            ),
            "peak_demand_reduction_pct": experiment["reductions"]["peak_power_pct"],
            "comfort_compliance_pct": None,
            "occupied_comfort_violation_hours": {
                "baseline": experiment["baseline"]["occupied_comfort_violation_hours"],
                "agent": experiment["agent"]["occupied_comfort_violation_hours"],
            },
            "action_counts": experiment["action_counts"],
            "carbon_accounting": experiment["carbon_accounting"],
            "label": "energyplus_experiment_results",
            "simulated": False,
            "synthetic_multiplier_applied": False,
            "experiment": experiment,
        }
    if data_mode == "energyplus":
        return {
            "building_id": building_id,
            "data_mode": "energyplus",
            "energy_usage_kwh": None,
            "baseline_energy_kwh": None,
            "estimated_savings_pct": None,
            "hvac_energy_kwh": None,
            "baseline_hvac_energy_kwh": None,
            "hvac_savings_pct": None,
            "cost_saved": None,
            "carbon_avoided_kg": None,
            "peak_demand_reduction_pct": None,
            "comfort_compliance_pct": None,
            "label": "energyplus_results_unavailable",
            "simulated": False,
            "synthetic_multiplier_applied": False,
            "experiment": experiment,
            "experiment_available": False,
            "missing_artifacts": experiment.get("missing_artifacts") or [],
            "evidence_note": (
                "No EnergyPlus experiment results found. "
                "Run the baseline and agent experiment scripts first. "
                "DATA_MODE=energyplus will not switch to mock automatically."
            ),
        }
    return {
        "building_id": building_id,
        "data_mode": "mock",
        "energy_usage_kwh": round(hub.twin_energy_kwh, 2),
        "baseline_energy_kwh": round(hub.baseline_energy_kwh, 2),
        "estimated_savings_pct": 0.0,
        "cost_saved": 0.0,
        "carbon_avoided_kg": 0.0,
        "peak_demand_reduction_pct": 0.0,
        "comfort_compliance_pct": hub.comfort_compliance,
        "label": "mock_twin_no_invented_savings",
        "simulated": True,
        "synthetic_multiplier_applied": False,
        "evidence_note": (
            "Mock mode reports live twin integrals only — no synthetic savings. "
            "Set DATA_MODE=energyplus for measured baseline-vs-agent results."
        ),
    }


@router.get("/experiments/comparison")
def experiments_comparison(
    user: CurrentUser,
    scenario: str = Query(default="default"),
) -> dict[str, Any]:
    payload = experiment_dashboard_payload(scenario)
    if not payload.get("available"):
        raise HTTPException(
            404,
            f"Experiment results unavailable under {results_root()} "
            f"(missing: {payload.get('missing_artifacts')})",
        )
    return payload


@router.get("/experiments/stream")
def experiments_stream(
    user: CurrentUser,
    scenario: str = Query(default="default"),
    limit: int = Query(default=500, ge=1, le=5000),
) -> dict[str, Any]:
    frames = load_stream_frames(scenario)[:limit]
    return {
        "scenario": scenario,
        "frame_count": len(frames),
        "frames": frames,
        "data_mode": "energyplus",
        "note": "Accelerated demo stream from results/*/stream.json",
    }


@router.get("/experiments/actions")
def experiments_actions(
    user: CurrentUser,
    scenario: str = Query(default="default"),
) -> dict[str, Any]:
    actions = load_actions(scenario)
    return {"scenario": scenario, "count": len(actions), "actions": actions}


@router.get("/experiments/scenarios")
def experiments_scenarios(user: CurrentUser) -> dict[str, Any]:
    consolidated = load_consolidated_scenarios()
    return {
        "consolidated": consolidated,
        "default": experiment_dashboard_payload("default"),
    }


@router.post("/experiments/safety-demo")
def experiments_safety_demo(user: CurrentUser) -> dict[str, Any]:
    """Deterministic unsafe-proposal demonstration (does not alter efficiency results)."""
    from twinpilot_simulator.ep_experiment import SafetyLimits, validate_setpoint_action

    unsafe = 35.0
    current = 23.9
    ok, reasons, disposition = validate_setpoint_action(
        proposed=unsafe,
        current=current,
        heating_setpoint=22.2,
        limits=SafetyLimits(),
        confidence=0.99,
        sensors_healthy=True,
        data_age_seconds=0.0,
        manual_override=False,
        llm_timed_out=False,
        mcp_failed=False,
    )
    result = {
        "demo": "unsafe_setpoint_rejection",
        "unsafe_proposal_c": unsafe,
        "current_safe_setpoint_c": current,
        "approved": ok,
        "disposition": disposition,
        "rejection_reasons": reasons,
        "fallback_action": f"retain_safe_setpoint={current}",
        "continued_operation": True,
        "contaminates_efficiency_experiment": False,
        "log_line": (
            f"UNSAFE_PROPOSAL rejected proposed={unsafe} retained={current} "
            f"reasons={reasons} disposition={disposition}"
        ),
    }
    # Also exercise SafetyShield model used by API apply path
    shield_result = shield.validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=current,
            proposed_value=unsafe,
            duration_minutes=60,
            paired_heating_setpoint=22.2,
        ),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.99,
        ),
    )
    result["safety_shield_valid"] = shield_result.valid
    result["safety_shield_blocking"] = shield_result.blocking_reasons
    return result


@router.post("/experiments/llm-fallback-demo")
def experiments_llm_fallback_demo(user: CurrentUser) -> dict[str, Any]:
    """Show LLM-unavailable path activating deterministic fallback (no actuation bypass)."""
    from twinpilot_simulator.ep_experiment import (
        SafetyLimits,
        propose_agent_cooling_setpoint,
        validate_setpoint_action,
    )

    limits = SafetyLimits()
    proposed, reason, confidence = propose_agent_cooling_setpoint(
        outdoor_c=30.0,
        zone_temps={"SPACE1-1": 24.0, "SPACE2-1": 24.1},
        occupancy={"SPACE1-1": 2.0, "SPACE2-1": 1.0},
        current_cooling_setpoint=23.9,
        limits=limits,
        hour=10,
    )
    ok, reasons, disposition = validate_setpoint_action(
        proposed=proposed,
        current=23.9,
        heating_setpoint=22.2,
        limits=limits,
        confidence=confidence,
        sensors_healthy=True,
        data_age_seconds=0.0,
        manual_override=False,
        llm_timed_out=True,
        mcp_failed=False,
    )
    return {
        "demo": "llm_unavailable_deterministic_fallback",
        "llm_status": "unavailable_timeout",
        "deterministic_proposal_c": proposed,
        "proposal_reason": reason,
        "safety_disposition": disposition,
        "blocking_reasons": reasons,
        "approved_for_actuation": ok,
        "fallback_action": "hold_last_safe_setpoint=23.9",
        "log_line": (
            f"LLM_TIMEOUT -> deterministic proposal={proposed} "
            f"disposition={disposition} reasons={reasons}"
        ),
    }


@router.get("/buildings/{building_id}/analytics/timeseries")
def analytics_timeseries(building_id: str, user: CurrentUser) -> dict[str, Any]:
    simulated = bool((hub.latest_state or {}).get("simulated", True))
    return {
        "building_id": building_id,
        "points": hub.kpi_history[-288:],
        "label": "mock_twin_demo_kpis" if simulated else "energyplus_live_state",
        "simulated": simulated,
    }


@router.get("/buildings/{building_id}/analytics/export")
def analytics_export(building_id: str, user: CurrentUser) -> dict[str, str]:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=[
            "timestamp",
            "power_kw",
            "baseline_power_kw",
            "carbon_intensity",
            "comfort_compliance",
            "baseline_energy_kwh",
            "twin_energy_kwh",
        ],
    )
    writer.writeheader()
    for row in hub.kpi_history:
        writer.writerow(row)
    return {"filename": f"twinpilot-{building_id}-analytics.csv", "csv": buf.getvalue()}


@router.get("/buildings/{building_id}/ledger")
def prediction_ledger(building_id: str, db: DbSession, user: CurrentUser) -> list[dict[str, Any]]:
    rows = (
        db.query(PredictionLedgerEntry)
        .filter(PredictionLedgerEntry.building_id == building_id)
        .order_by(PredictionLedgerEntry.created_at.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "id": r.id,
            "decision_id": r.decision_id,
            "plan_id": r.plan_id,
            "predicted_json": r.predicted_json,
            "realized_json": r.realized_json,
            "error_json": r.error_json,
            "confidence_before": r.confidence_before,
            "confidence_after": r.confidence_after,
            "rollback_required": r.rollback_required,
            "explanation": r.explanation,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/buildings/{building_id}/audit")
def audit_log(building_id: str, db: DbSession, user: CurrentUser) -> list[dict[str, Any]]:
    rows = (
        db.query(AuditEvent)
        .filter(AuditEvent.building_id == building_id)
        .order_by(AuditEvent.timestamp.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "id": a.id,
            "user_id": a.user_id,
            "event_type": a.event_type,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "previous_value_json": a.previous_value_json,
            "new_value_json": a.new_value_json,
            "reason": a.reason,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        }
        for a in rows
    ]


# ── Demo / simulator controls ─────────────────────────────────────────
@router.get("/demo/scenarios")
def demo_scenarios(user: CurrentUser) -> list[dict[str, str]]:
    return [
        {"id": "normal_hot_day", "name": "Normal hot day"},
        {"id": "occupancy_spike", "name": "Unexpected occupancy spike"},
        {"id": "carbon_intensive", "name": "Carbon-intensive grid period"},
        {"id": "faulty_sensor", "name": "Faulty temperature sensor"},
        {"id": "infeasible_target", "name": "Infeasible target"},
        {"id": "simulation_failure", "name": "Simulation service failure"},
        {"id": "rollback", "name": "Successful rollback"},
    ]


@router.post("/demo/scenarios/{scenario_id}/start")
def start_scenario(scenario_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    try:
        result = hub.start_scenario(db, scenario_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc
    _audit(
        db,
        user_id=user.id,
        building_id=hub.building_id,
        event_type="scenario_started",
        entity_type="scenario",
        entity_id=scenario_id,
        reason="Demo scenario start",
    )
    db.commit()
    return result


@router.post("/demo/scenarios/reset")
def reset_scenarios(db: DbSession, user: CurrentUser) -> dict[str, Any]:
    result = hub.reset_demo(db)
    return result


@router.post("/demo/speed")
def demo_speed(payload: DemoSpeedRequest, user: CurrentUser) -> dict[str, Any]:
    if hasattr(hub.simulator, "set_speed"):
        hub.simulator.set_speed(payload.speed)  # type: ignore[attr-defined]
    elif hasattr(hub.simulator, "_fallback"):
        hub.simulator._fallback.set_speed(payload.speed)  # type: ignore[attr-defined]
    return {"speed": payload.speed}


@router.post("/demo/playback/{action}")
def demo_playback(action: str, user: CurrentUser) -> dict[str, Any]:
    sim = hub.simulator
    if hasattr(sim, "_fallback"):
        sim = sim._fallback  # type: ignore[attr-defined]
    if action == "pause" and hasattr(sim, "pause"):
        sim.pause()
    elif action == "resume" and hasattr(sim, "resume"):
        sim.resume()
    elif action == "step" and hasattr(sim, "step"):
        hub.latest_state = sim.step(1).model_dump()
    elif action == "reset":
        hub.latest_state = hub.simulator.reset().model_dump()
    else:
        raise HTTPException(400, "Unknown playback action")
    return {"action": action, "state": hub.latest_state}


@router.post("/buildings/{building_id}/what-if")
def what_if(building_id: str, payload: WhatIfRequest, user: CurrentUser) -> dict[str, Any]:
    state = hub.simulator.get_state().model_dump()
    if payload.outdoor_temperature is not None:
        state["outdoor_temperature"] = payload.outdoor_temperature
    if payload.electricity_price is not None:
        state["electricity_tariff"] = payload.electricity_price
    if payload.grid_carbon_intensity is not None:
        state["grid_carbon_intensity"] = payload.grid_carbon_intensity
    if payload.occupancy_level is not None:
        for z in state["zones"].values():
            z["occupancy_count"] = int(z["occupancy_count"] * payload.occupancy_level)
    for zid in payload.sensor_failures:
        if zid in state["zones"]:
            state["zones"][zid]["sensor_failed"] = True
            state["zones"][zid]["temperature"] = 55.0

    weights = ObjectiveWeights()
    obs = BuildingObservation(
        outdoor_temperature=state["outdoor_temperature"],
        carbon_intensity=state["grid_carbon_intensity"],
        electricity_tariff=state["electricity_tariff"],
        total_power_kw=state["total_building_power_kw"],
        occupancy_total=sum(z["occupancy_count"] for z in state["zones"].values()),
        hour=12,
        zones=state["zones"],
        peak_window=True,
        carbon_rising=state["grid_carbon_intensity"] > 800,
    )
    plans = generate_candidate_plans(
        obs,
        weights,
        energy_target_pct=payload.energy_saving_target,
        zero_comfort_deviation=bool(payload.energy_saving_target and payload.energy_saving_target >= 40),
    )
    by_source = {p.source.value: p for p in plans}
    return {
        "label": "simulated results — not verified real-building savings",
        "baseline": by_source.get("FIXED_BASELINE").metrics.model_dump()
        if "FIXED_BASELINE" in by_source
        else {},
        "rule_based": by_source.get("RULE_BASED").metrics.model_dump()
        if "RULE_BASED" in by_source
        else {},
        "twinpilot": by_source.get("BALANCED").metrics.model_dump()
        if "BALANCED" in by_source
        else {},
        "horizon_steps": payload.time_horizon_steps,
    }


# ── Assistant ─────────────────────────────────────────────────────────
@router.post("/assistant/chat")
async def assistant_chat(
    payload: AssistantChatRequest,
    db: DbSession,
    user: CurrentUser,
    request: Request,
) -> dict[str, Any]:
    enforce_assistant_rate_limit(request)
    building = db.get(Building, payload.building_id)
    if not building:
        raise HTTPException(404, "Building not found")
    alerts = (
        db.query(Alert)
        .filter(Alert.building_id == payload.building_id, Alert.status != "RESOLVED")
        .limit(20)
        .all()
    )
    decision = (
        db.query(Decision)
        .filter(Decision.building_id == payload.building_id)
        .order_by(Decision.created_at.desc())
        .first()
    )
    plans = (
        db.query(ControlPlan)
        .filter(ControlPlan.building_id == payload.building_id)
        .order_by(ControlPlan.created_at.desc())
        .limit(8)
        .all()
    )
    agent = get_agent_provider(
        settings.agent_provider,
        ollama_base_url=settings.ollama_base_url,
        ollama_model=settings.ollama_model,
    )
    out = await agent.explain(
        {
            "question": payload.message,
            "mode": building.current_mode,
            "decision": {
                "selected_plan_id": decision.selected_plan_id if decision else None,
                "explanation": decision.explanation if decision else None,
                "validation_status": decision.validation_status if decision else None,
                "applied_action_json": decision.applied_action_json if decision else None,
            },
            "alerts": [
                {"alert_type": a.alert_type, "severity": a.severity, "title": a.title} for a in alerts
            ],
            "plans": [
                {
                    "id": p.id,
                    "objective_score": p.objective_score,
                    "feasibility": p.feasibility,
                    "source": p.source,
                    "confidence": p.confidence,
                    "predicted_metrics_json": p.predicted_metrics_json,
                }
                for p in plans
            ],
        }
    )
    conv = None
    if payload.conversation_id:
        conv = db.get(AssistantConversation, payload.conversation_id)
    if not conv:
        conv = AssistantConversation(
            user_id=user.id,
            building_id=payload.building_id,
            title=payload.message[:80],
            messages_json=[],
        )
        db.add(conv)
        db.flush()
    messages = list(conv.messages_json or [])
    messages.append({"role": "user", "content": payload.message})
    messages.append({"role": "assistant", "content": out.model_dump()})
    conv.messages_json = messages
    db.commit()
    return {
        "conversation_id": conv.id,
        "answer": out.model_dump(),
        "evidence": {
            "mode": building.current_mode,
            "active_alerts": len(alerts),
            "decision_id": decision.id if decision else None,
        },
    }


@router.get("/assistant/conversations")
def list_conversations(db: DbSession, user: CurrentUser) -> list[dict[str, Any]]:
    rows = (
        db.query(AssistantConversation)
        .filter(AssistantConversation.user_id == user.id)
        .order_by(AssistantConversation.created_at.desc())
        .limit(50)
        .all()
    )
    return [{"id": c.id, "title": c.title, "building_id": c.building_id} for c in rows]


@router.get("/assistant/conversations/{conversation_id}")
def get_conversation(conversation_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    conv = db.get(AssistantConversation, conversation_id)
    if not conv or conv.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    return {"id": conv.id, "title": conv.title, "messages": conv.messages_json}


# ── Settings helpers ──────────────────────────────────────────────────
def _constraints_dict(row: ConstraintPolicy) -> dict[str, Any]:
    return {
        "id": row.id,
        "min_cooling_setpoint": row.min_cooling_setpoint,
        "max_cooling_setpoint": row.max_cooling_setpoint,
        "min_heating_setpoint": row.min_heating_setpoint,
        "max_heating_setpoint": row.max_heating_setpoint,
        "max_setpoint_change_per_interval": row.max_setpoint_change_per_interval,
        "minimum_ventilation": row.minimum_ventilation,
        "maximum_control_duration": row.maximum_control_duration,
        "minimum_confidence_for_autonomy": row.minimum_confidence_for_autonomy,
        "maximum_data_age_seconds": row.maximum_data_age_seconds,
    }


@router.get("/buildings/{building_id}/constraints")
def get_constraints(building_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    row = db.query(ConstraintPolicy).filter(ConstraintPolicy.building_id == building_id).first()
    if not row:
        raise HTTPException(404, "Constraints not found")
    return _constraints_dict(row)


@router.patch("/buildings/{building_id}/constraints")
def patch_constraints(
    building_id: str,
    payload: ConstraintUpdateRequest,
    db: DbSession,
    user: User = Depends(require_permission("constraint_modify")),
) -> dict[str, Any]:
    row = db.query(ConstraintPolicy).filter(ConstraintPolicy.building_id == building_id).first()
    if not row:
        raise HTTPException(404, "Constraints not found")
    previous = _constraints_dict(row)
    for field in (
        "min_cooling_setpoint",
        "max_cooling_setpoint",
        "min_heating_setpoint",
        "max_heating_setpoint",
        "max_setpoint_change_per_interval",
        "minimum_ventilation",
        "maximum_control_duration",
        "minimum_confidence_for_autonomy",
        "maximum_data_age_seconds",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(row, field, value)
    if row.min_cooling_setpoint >= row.max_cooling_setpoint:
        raise HTTPException(400, "min_cooling_setpoint must be below max_cooling_setpoint")
    if row.min_heating_setpoint >= row.max_heating_setpoint:
        raise HTTPException(400, "min_heating_setpoint must be below max_heating_setpoint")
    _audit(
        db,
        user_id=user.id,
        building_id=building_id,
        event_type="constraints_updated",
        entity_type="constraint_policy",
        entity_id=row.id,
        reason=payload.reason,
        previous=previous,
        new=_constraints_dict(row),
    )
    db.commit()
    db.refresh(row)
    return _constraints_dict(row)


@router.patch("/buildings/{building_id}", response_model=BuildingOut)
def patch_building(
    building_id: str,
    payload: BuildingUpdateRequest,
    db: DbSession,
    user: User = Depends(require_roles(UserRole.ADMINISTRATOR)),
) -> Building:
    building = db.get(Building, building_id)
    if not building:
        raise HTTPException(404, "Building not found")
    previous = {
        "name": building.name,
        "location": building.location,
        "timezone": building.timezone,
        "area_m2": building.area_m2,
        "building_type": building.building_type,
    }
    for field in ("name", "location", "timezone", "area_m2", "building_type"):
        value = getattr(payload, field)
        if value is not None:
            setattr(building, field, value)
    _audit(
        db,
        user_id=user.id,
        building_id=building_id,
        event_type="building_updated",
        entity_type="building",
        entity_id=building_id,
        reason=payload.reason,
        previous=previous,
        new={
            "name": building.name,
            "location": building.location,
            "timezone": building.timezone,
            "area_m2": building.area_m2,
            "building_type": building.building_type,
        },
    )
    db.commit()
    db.refresh(building)
    return building


@router.get("/buildings/{building_id}/comfort-policy")
def get_comfort_policy(building_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    row = db.query(ComfortPolicy).filter(ComfortPolicy.building_id == building_id).first()
    if not row:
        raise HTTPException(404, "Comfort policy not found")
    return {
        "id": row.id,
        "occupied_min_temperature": row.occupied_min_temperature,
        "occupied_max_temperature": row.occupied_max_temperature,
        "unoccupied_min_temperature": row.unoccupied_min_temperature,
        "unoccupied_max_temperature": row.unoccupied_max_temperature,
        "max_violation_minutes": row.max_violation_minutes,
        "humidity_min": row.humidity_min,
        "humidity_max": row.humidity_max,
        "co2_max_ppm": row.co2_max_ppm,
    }


@router.get("/buildings/{building_id}/goals")
def get_goals(building_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    row = (
        db.query(GoalProfile)
        .filter(GoalProfile.building_id == building_id, GoalProfile.active.is_(True))
        .first()
    )
    if not row:
        raise HTTPException(404, "Goals not found")
    return {
        "id": row.id,
        "name": row.name,
        "energy_weight": row.energy_weight,
        "cost_weight": row.cost_weight,
        "carbon_weight": row.carbon_weight,
        "comfort_weight": row.comfort_weight,
        "peak_weight": row.peak_weight,
        "equipment_weight": row.equipment_weight,
    }


@router.patch("/buildings/{building_id}/goals")
def patch_goals(
    building_id: str,
    payload: GoalUpdateRequest,
    db: DbSession,
    user: User = Depends(require_roles(UserRole.ADMINISTRATOR, UserRole.FACILITY_MANAGER)),
) -> dict[str, Any]:
    row = (
        db.query(GoalProfile)
        .filter(GoalProfile.building_id == building_id, GoalProfile.active.is_(True))
        .first()
    )
    if not row:
        raise HTTPException(404, "Goals not found")
    previous = {
        "name": row.name,
        "energy_weight": row.energy_weight,
        "cost_weight": row.cost_weight,
        "carbon_weight": row.carbon_weight,
        "comfort_weight": row.comfort_weight,
        "peak_weight": row.peak_weight,
        "equipment_weight": row.equipment_weight,
    }
    if payload.name is not None:
        row.name = payload.name
    for field in (
        "energy_weight",
        "cost_weight",
        "carbon_weight",
        "comfort_weight",
        "peak_weight",
        "equipment_weight",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(row, field, value)
    # Normalize via ObjectiveWeights
    weights = ObjectiveWeights(
        energy_weight=row.energy_weight,
        cost_weight=row.cost_weight,
        carbon_weight=row.carbon_weight,
        comfort_weight=row.comfort_weight,
        peak_weight=row.peak_weight,
        equipment_weight=row.equipment_weight,
    )
    row.energy_weight = weights.energy_weight
    row.cost_weight = weights.cost_weight
    row.carbon_weight = weights.carbon_weight
    row.comfort_weight = weights.comfort_weight
    row.peak_weight = weights.peak_weight
    row.equipment_weight = weights.equipment_weight
    _audit(
        db,
        user_id=user.id,
        building_id=building_id,
        event_type="goals_updated",
        entity_type="goal_profile",
        entity_id=row.id,
        reason=payload.reason,
        previous=previous,
        new={
            "name": row.name,
            "energy_weight": row.energy_weight,
            "cost_weight": row.cost_weight,
            "carbon_weight": row.carbon_weight,
            "comfort_weight": row.comfort_weight,
            "peak_weight": row.peak_weight,
            "equipment_weight": row.equipment_weight,
        },
    )
    db.commit()
    return {
        "id": row.id,
        "name": row.name,
        "energy_weight": row.energy_weight,
        "cost_weight": row.cost_weight,
        "carbon_weight": row.carbon_weight,
        "comfort_weight": row.comfort_weight,
        "peak_weight": row.peak_weight,
        "equipment_weight": row.equipment_weight,
    }


@router.get("/users", response_model=list[UserOut])
def list_users(
    db: DbSession,
    user: User = Depends(require_roles(UserRole.ADMINISTRATOR)),
) -> list[User]:
    return list(db.scalars(select(User)).all())


@router.post("/users", response_model=UserOut, status_code=201)
def create_user(
    payload: UserCreateRequest,
    db: DbSession,
    user: User = Depends(require_permission("user_manage")),
) -> User:
    try:
        role = UserRole(payload.role)
    except ValueError as exc:
        raise HTTPException(400, f"Invalid role: {payload.role}") from exc
    existing = db.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(409, "User with this email already exists")
    created = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=role.value,
        is_active=True,
    )
    db.add(created)
    db.flush()
    _audit(
        db,
        user_id=user.id,
        building_id=hub.building_id,
        event_type="user_created",
        entity_type="user",
        entity_id=created.id,
        reason=payload.reason,
        new={"email": created.email, "role": created.role, "name": created.name},
    )
    db.commit()
    db.refresh(created)
    return created


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    db: DbSession,
    user: User = Depends(require_permission("user_manage")),
) -> User:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(404, "User not found")
    previous = {"name": target.name, "role": target.role, "is_active": target.is_active}
    if payload.name is not None:
        target.name = payload.name
    if payload.role is not None:
        try:
            target.role = UserRole(payload.role).value
        except ValueError as exc:
            raise HTTPException(400, f"Invalid role: {payload.role}") from exc
    if payload.is_active is not None:
        if target.id == user.id and payload.is_active is False:
            raise HTTPException(400, "Administrators cannot deactivate themselves")
        target.is_active = payload.is_active
    _audit(
        db,
        user_id=user.id,
        building_id=hub.building_id,
        event_type="user_updated",
        entity_type="user",
        entity_id=target.id,
        reason=payload.reason,
        previous=previous,
        new={"name": target.name, "role": target.role, "is_active": target.is_active},
    )
    db.commit()
    db.refresh(target)
    return target

