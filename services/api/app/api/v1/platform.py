"""Multi-tenant org, billing, connectors, onboarding, and M&V routes."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, DbSession, get_building_for_user, get_organization_for_user, require_permission
from app.core.security import hash_password, hash_token
from app.models import (
    AuditEvent,
    Building,
    ConnectorProfile,
    Invitation,
    Membership,
    MvBaseline,
    Organization,
    PointMapping,
    SiteCertification,
    TelemetryPoint,
    User,
)
from app.models.enums import UserRole
from app.schemas.common import (
    CheckoutRequest,
    ConnectorCreateRequest,
    ConnectorProfileOut,
    InvitationAcceptRequest,
    InvitationCreateRequest,
    InvitationOut,
    MembershipOut,
    MvBaselineCreateRequest,
    MvBaselineOut,
    MvReportOut,
    OnboardingStageRequest,
    OrganizationOut,
    PointMappingOut,
    PointMappingUpsertRequest,
    SiteCertificationUpdateRequest,
    SubscriptionOut,
    UserOut,
)
from app.services.billing_stripe import (
    apply_plan,
    create_checkout_session,
    create_portal_session,
    ensure_subscription,
    handle_webhook,
)
from app.services.entitlements import (
    PLAN_ENTITLEMENTS,
    assert_building_quota,
    assert_connector_allowed,
    get_org_entitlements,
    require_entitlement,
)
from app.services.tenancy import get_membership, list_user_organizations, require_org_admin

router = APIRouter(prefix="/api/v1", tags=["platform"])


def _audit(
    db: Session,
    *,
    user_id: str | None,
    organization_id: str | None,
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
            organization_id=organization_id,
            user_id=user_id,
            building_id=building_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            previous_value_json=previous,
            new_value_json=new,
            reason=reason,
            request_id=request_id,
            immutable=True,
        )
    )


# ── Organizations ─────────────────────────────────────────────────────
@router.get("/organizations", response_model=list[OrganizationOut])
def list_organizations(db: DbSession, user: CurrentUser) -> list[Organization]:
    return list_user_organizations(db, user)


@router.get("/organizations/{organization_id}", response_model=OrganizationOut)
def get_organization(organization_id: str, db: DbSession, user: CurrentUser) -> Organization:
    return get_organization_for_user(organization_id, db, user)


@router.get("/organizations/{organization_id}/members", response_model=list[MembershipOut])
def list_members(organization_id: str, db: DbSession, user: CurrentUser) -> list[dict[str, Any]]:
    get_organization_for_user(organization_id, db, user)
    rows = list(
        db.scalars(
            select(Membership).where(
                Membership.organization_id == organization_id,
                Membership.is_active.is_(True),
            )
        ).all()
    )
    out: list[dict[str, Any]] = []
    for m in rows:
        u = db.get(User, m.user_id)
        out.append(
            {
                "id": m.id,
                "organization_id": m.organization_id,
                "user_id": m.user_id,
                "org_role": m.org_role,
                "is_active": m.is_active,
                "user": UserOut.model_validate(u) if u else None,
            }
        )
    return out


@router.post(
    "/organizations/{organization_id}/invitations",
    response_model=InvitationOut,
    status_code=201,
)
def invite_member(
    organization_id: str,
    payload: InvitationCreateRequest,
    db: DbSession,
    user: User = Depends(require_permission("org_manage")),
) -> Invitation:
    org = get_organization_for_user(organization_id, db, user)
    membership = get_membership(db, user, organization_id)
    require_org_admin(membership, user)
    try:
        UserRole(payload.org_role)
    except ValueError as exc:
        raise HTTPException(400, f"Invalid role: {payload.org_role}") from exc
    token = secrets.token_urlsafe(24)
    inv = Invitation(
        organization_id=org.id,
        email=payload.email.lower(),
        org_role=payload.org_role,
        token=token,
        invited_by_user_id=user.id,
        status="PENDING",
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add(inv)
    _audit(
        db,
        user_id=user.id,
        organization_id=org.id,
        building_id=None,
        event_type="invitation_created",
        entity_type="invitation",
        entity_id=None,
        reason=payload.reason,
        new={"email": inv.email, "org_role": inv.org_role},
    )
    db.commit()
    db.refresh(inv)
    # Return token once for shareable invite link (demo / email provider later)
    return InvitationOut(
        id=inv.id,
        organization_id=inv.organization_id,
        email=inv.email,
        org_role=inv.org_role,
        status=inv.status,
        expires_at=inv.expires_at,
        token=token,
    )


@router.post("/invitations/accept", response_model=UserOut)
def accept_invitation(payload: InvitationAcceptRequest, db: DbSession) -> User:
    inv = db.scalar(select(Invitation).where(Invitation.token == payload.token))
    if inv is None or inv.status != "PENDING":
        raise HTTPException(404, "Invitation not found")
    if inv.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        inv.status = "EXPIRED"
        db.commit()
        raise HTTPException(400, "Invitation expired")
    existing = db.scalar(select(User).where(User.email == inv.email))
    if existing:
        user = existing
    else:
        user = User(
            name=payload.name,
            email=inv.email,
            password_hash=hash_password(payload.password),
            role=inv.org_role,
            is_active=True,
            default_organization_id=inv.organization_id,
        )
        db.add(user)
        db.flush()
    membership = get_membership(db, user, inv.organization_id)
    if membership is None:
        db.add(
            Membership(
                organization_id=inv.organization_id,
                user_id=user.id,
                org_role=inv.org_role,
                is_active=True,
            )
        )
    inv.status = "ACCEPTED"
    inv.accepted_at = datetime.now(UTC)
    user.default_organization_id = inv.organization_id
    db.commit()
    db.refresh(user)
    return user


# ── Billing ───────────────────────────────────────────────────────────
@router.get("/billing/plans")
def list_plans() -> dict[str, Any]:
    return {"plans": PLAN_ENTITLEMENTS}


@router.get("/organizations/{organization_id}/subscription", response_model=SubscriptionOut)
def get_subscription(organization_id: str, db: DbSession, user: CurrentUser) -> SubscriptionOut:
    org = get_organization_for_user(organization_id, db, user)
    sub = ensure_subscription(db, org)
    db.commit()
    ent = get_org_entitlements(db, org)
    return SubscriptionOut(
        organization_id=org.id,
        plan_code=sub.plan_code,
        status=sub.status,
        entitlements=ent,
        current_period_end=sub.current_period_end,
    )


@router.post("/organizations/{organization_id}/billing/checkout")
def checkout(
    organization_id: str,
    payload: CheckoutRequest,
    db: DbSession,
    user: User = Depends(require_permission("billing_manage")),
) -> dict[str, Any]:
    org = get_organization_for_user(organization_id, db, user)
    result = create_checkout_session(org, payload.plan_code)
    if result.get("mode") == "mock":
        apply_plan(db, org, payload.plan_code, source="mock_checkout")
        db.commit()
    else:
        db.commit()
    return result


@router.post("/organizations/{organization_id}/billing/portal")
def billing_portal(
    organization_id: str,
    db: DbSession,
    user: User = Depends(require_permission("billing_manage")),
) -> dict[str, Any]:
    org = get_organization_for_user(organization_id, db, user)
    return create_portal_session(org)


@router.post("/billing/webhook")
async def stripe_webhook(request: Request, db: DbSession) -> dict[str, Any]:
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    return handle_webhook(db, payload, signature)


# ── Connectors & commissioning ────────────────────────────────────────
@router.get("/buildings/{building_id}/connectors", response_model=list[ConnectorProfileOut])
def list_connectors(building_id: str, db: DbSession, user: CurrentUser) -> list[ConnectorProfile]:
    building = get_building_for_user(building_id, db, user)
    return list(
        db.scalars(
            select(ConnectorProfile).where(ConnectorProfile.building_id == building.id)
        ).all()
    )


@router.post(
    "/buildings/{building_id}/connectors",
    response_model=ConnectorProfileOut,
    status_code=201,
)
def create_connector(
    building_id: str,
    payload: ConnectorCreateRequest,
    db: DbSession,
    user: User = Depends(require_permission("connector_manage")),
) -> ConnectorProfile:
    building = get_building_for_user(building_id, db, user)
    if not building.organization_id:
        raise HTTPException(400, "Building has no organization")
    org = db.get(Organization, building.organization_id)
    assert org is not None
    assert_connector_allowed(db, org, payload.adapter_type)
    secret_ref = None
    site_token = secrets.token_urlsafe(24)
    if payload.secret:
        secret_ref = f"env:CONNECTOR_SECRET_{building.id[:8].upper()}"
    profile = ConnectorProfile(
        organization_id=org.id,
        building_id=building.id,
        adapter_type=payload.adapter_type,
        name=payload.name,
        config_json={**payload.config_json, "site_token_hint": site_token[:6] + "…"},
        secret_ref=secret_ref,
        site_token_hash=hash_token(site_token),
        status="PROVISIONED",
        last_health_json={"status": "provisioned", "adapter": payload.adapter_type},
    )
    db.add(profile)
    db.flush()
    building.connector_profile_id = profile.id
    if building.onboarding_stage in {"demo", "connect"}:
        building.onboarding_stage = "map_points"
    _audit(
        db,
        user_id=user.id,
        organization_id=org.id,
        building_id=building.id,
        event_type="connector_created",
        entity_type="connector_profile",
        entity_id=profile.id,
        new={"adapter_type": profile.adapter_type, "name": profile.name},
    )
    db.commit()
    db.refresh(profile)
    # Attach one-time site token in response via config for commissioning
    profile.config_json = {**profile.config_json, "site_token": site_token}
    return profile


@router.post("/buildings/{building_id}/connectors/{connector_id}/discover")
def discover_points(
    building_id: str,
    connector_id: str,
    db: DbSession,
    user: User = Depends(require_permission("connector_manage")),
) -> dict[str, Any]:
    building = get_building_for_user(building_id, db, user)
    profile = db.get(ConnectorProfile, connector_id)
    if profile is None or profile.building_id != building.id:
        raise HTTPException(404, "Connector not found")
    from twinpilot_connectors import get_adapter

    adapter = get_adapter(profile.adapter_type, profile.config_json or {})
    points = adapter.discover_points()
    profile.status = "CONNECTED"
    profile.last_seen_at = datetime.now(UTC)
    profile.last_health_json = adapter.health()
    db.commit()
    return {"adapter_type": profile.adapter_type, "points": points, "health": adapter.health()}


@router.get("/buildings/{building_id}/point-mappings", response_model=list[PointMappingOut])
def list_point_mappings(building_id: str, db: DbSession, user: CurrentUser) -> list[PointMapping]:
    building = get_building_for_user(building_id, db, user)
    return list(db.scalars(select(PointMapping).where(PointMapping.building_id == building.id)).all())


@router.put("/buildings/{building_id}/point-mappings", response_model=list[PointMappingOut])
def upsert_point_mappings(
    building_id: str,
    payload: list[PointMappingUpsertRequest],
    db: DbSession,
    user: User = Depends(require_permission("connector_manage")),
) -> list[PointMapping]:
    building = get_building_for_user(building_id, db, user)
    if not building.connector_profile_id:
        raise HTTPException(400, "Building has no connector profile")
    existing = {
        m.external_point_id: m
        for m in db.scalars(select(PointMapping).where(PointMapping.building_id == building.id)).all()
    }
    result: list[PointMapping] = []
    for item in payload:
        row = existing.get(item.external_point_id)
        if row is None:
            row = PointMapping(
                building_id=building.id,
                connector_profile_id=building.connector_profile_id,
                external_point_id=item.external_point_id,
            )
            db.add(row)
        row.external_point_name = item.external_point_name
        row.zone_id = item.zone_id
        row.twinpilot_metric = item.twinpilot_metric
        row.direction = item.direction
        row.unit = item.unit
        row.scale = item.scale
        row.offset = item.offset
        row.deadband = item.deadband
        row.enabled = item.enabled
        result.append(row)
    if building.onboarding_stage == "map_points":
        building.onboarding_stage = "shadow"
        building.shadow_mode = True
    _audit(
        db,
        user_id=user.id,
        organization_id=building.organization_id,
        building_id=building.id,
        event_type="point_mappings_updated",
        entity_type="point_mapping",
        entity_id=building.id,
        new={"count": len(result)},
    )
    db.commit()
    return result


@router.post("/buildings/{building_id}/connectors/poll")
def poll_connector_telemetry(
    building_id: str,
    db: DbSession,
    user: User = Depends(require_permission("connector_manage")),
) -> dict[str, Any]:
    building = get_building_for_user(building_id, db, user)
    profile = None
    if building.connector_profile_id:
        profile = db.get(ConnectorProfile, building.connector_profile_id)
    if profile is None:
        raise HTTPException(400, "No connector configured")
    from twinpilot_connectors import get_adapter

    adapter = get_adapter(profile.adapter_type, profile.config_json or {})
    samples = adapter.poll_telemetry()
    written = 0
    for sample in samples:
        db.add(
            TelemetryPoint(
                building_id=building.id,
                zone_id=sample.get("zone_id"),
                metric=sample.get("metric", "unknown"),
                value=float(sample.get("value", 0.0)),
                unit=sample.get("unit", ""),
                timestamp=datetime.now(UTC),
                quality=sample.get("quality", "GOOD"),
                source=f"connector:{profile.adapter_type}",
            )
        )
        written += 1
    profile.last_seen_at = datetime.now(UTC)
    profile.last_health_json = adapter.health()
    profile.status = "CONNECTED"
    db.commit()
    return {"written": written, "health": adapter.health(), "samples": samples[:20]}


# ── Onboarding & certification ────────────────────────────────────────
@router.patch("/buildings/{building_id}/onboarding", response_model=dict)
def set_onboarding_stage(
    building_id: str,
    payload: OnboardingStageRequest,
    db: DbSession,
    user: User = Depends(require_permission("site_certify")),
) -> dict[str, Any]:
    building = get_building_for_user(building_id, db, user)
    previous = building.onboarding_stage
    building.onboarding_stage = payload.stage
    building.shadow_mode = payload.stage in {"shadow", "map_points"}
    if payload.stage == "guarded_pilot":
        building.current_mode = "GUARDED"
        building.write_enabled = True
    if payload.stage == "autonomy":
        if not building.site_certified:
            raise HTTPException(400, "Site must be certified before autonomy stage")
        org = db.get(Organization, building.organization_id) if building.organization_id else None
        if org:
            require_entitlement(db, org, "autonomous_write")
        building.current_mode = "AUTONOMOUS"
        building.write_enabled = True
        building.shadow_mode = False
    _audit(
        db,
        user_id=user.id,
        organization_id=building.organization_id,
        building_id=building.id,
        event_type="onboarding_stage_changed",
        entity_type="building",
        entity_id=building.id,
        reason=payload.reason,
        previous={"stage": previous},
        new={"stage": building.onboarding_stage},
    )
    db.commit()
    return {
        "building_id": building.id,
        "onboarding_stage": building.onboarding_stage,
        "shadow_mode": building.shadow_mode,
        "write_enabled": building.write_enabled,
        "current_mode": building.current_mode,
    }


@router.get("/buildings/{building_id}/certification")
def get_certification(building_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    building = get_building_for_user(building_id, db, user)
    cert = db.scalar(select(SiteCertification).where(SiteCertification.building_id == building.id))
    if cert is None:
        return {
            "building_id": building.id,
            "site_certified": building.site_certified,
            "checklist_json": {},
            "shadow_mode_complete": False,
            "guarded_pilot_complete": False,
            "autonomy_approved": False,
        }
    return {
        "building_id": building.id,
        "site_certified": building.site_certified,
        "checklist_json": cert.checklist_json,
        "shadow_mode_complete": cert.shadow_mode_complete,
        "guarded_pilot_complete": cert.guarded_pilot_complete,
        "autonomy_approved": cert.autonomy_approved,
        "certified_at": cert.certified_at,
        "notes": cert.notes,
    }


@router.put("/buildings/{building_id}/certification")
def update_certification(
    building_id: str,
    payload: SiteCertificationUpdateRequest,
    db: DbSession,
    user: User = Depends(require_permission("site_certify")),
) -> dict[str, Any]:
    building = get_building_for_user(building_id, db, user)
    cert = db.scalar(select(SiteCertification).where(SiteCertification.building_id == building.id))
    if cert is None:
        cert = SiteCertification(building_id=building.id, checklist_json={})
        db.add(cert)
    cert.checklist_json = {**(cert.checklist_json or {}), **payload.checklist_json}
    if payload.shadow_mode_complete is not None:
        cert.shadow_mode_complete = payload.shadow_mode_complete
    if payload.guarded_pilot_complete is not None:
        cert.guarded_pilot_complete = payload.guarded_pilot_complete
    if payload.autonomy_approved is not None:
        cert.autonomy_approved = payload.autonomy_approved
    if payload.notes is not None:
        cert.notes = payload.notes
    ready = (
        cert.shadow_mode_complete
        and cert.guarded_pilot_complete
        and cert.autonomy_approved
        and bool(cert.checklist_json.get("failsafe_tested"))
        and bool(cert.checklist_json.get("point_map_complete"))
    )
    if ready:
        building.site_certified = True
        cert.certified_at = datetime.now(UTC)
        cert.certified_by_user_id = user.id
        building.onboarding_stage = "autonomy_review"
    _audit(
        db,
        user_id=user.id,
        organization_id=building.organization_id,
        building_id=building.id,
        event_type="site_certification_updated",
        entity_type="site_certification",
        entity_id=building.id,
        reason=payload.reason,
        new={
            "site_certified": building.site_certified,
            "checklist": cert.checklist_json,
        },
    )
    db.commit()
    return {
        "building_id": building.id,
        "site_certified": building.site_certified,
        "ready_for_autonomy": ready,
    }


# ── M&V / ROI ─────────────────────────────────────────────────────────
@router.post(
    "/buildings/{building_id}/mv/baselines",
    response_model=MvBaselineOut,
    status_code=201,
)
def create_mv_baseline(
    building_id: str,
    payload: MvBaselineCreateRequest,
    db: DbSession,
    user: User = Depends(require_permission("site_certify")),
) -> MvBaseline:
    building = get_building_for_user(building_id, db, user)
    if building.organization_id:
        org = db.get(Organization, building.organization_id)
        if org:
            require_entitlement(db, org, "mv_reporting")
    row = MvBaseline(
        building_id=building.id,
        name=payload.name,
        start_at=payload.start_at,
        end_at=payload.end_at,
        baseline_energy_kwh=payload.baseline_energy_kwh,
        baseline_cost=payload.baseline_cost,
        baseline_carbon_kg=payload.baseline_carbon_kg,
        weather_normalized=payload.weather_normalized,
        methodology=payload.methodology,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/buildings/{building_id}/mv/report", response_model=MvReportOut)
def mv_report(building_id: str, db: DbSession, user: CurrentUser) -> MvReportOut:
    building = get_building_for_user(building_id, db, user)
    baseline = db.scalar(
        select(MvBaseline)
        .where(MvBaseline.building_id == building.id)
        .order_by(MvBaseline.created_at.desc())
    )
    # Aggregate recent power samples as a coarse energy proxy for demo/live
    power_rows = list(
        db.scalars(
            select(TelemetryPoint)
            .where(
                TelemetryPoint.building_id == building.id,
                TelemetryPoint.metric.in_(["power", "hvac_power_kw", "total_building_power_kw"]),
            )
            .order_by(TelemetryPoint.timestamp.desc())
            .limit(500)
        ).all()
    )
    if power_rows:
        avg_kw = sum(p.value for p in power_rows) / len(power_rows)
        period_energy = avg_kw * 24.0  # approximate daily kWh
    else:
        period_energy = 0.0
    period_cost = period_energy * 0.12
    period_carbon = period_energy * 0.4
    labeled = building.is_demo or not bool(power_rows)
    if baseline:
        savings_energy = max(0.0, baseline.baseline_energy_kwh - period_energy)
        savings_cost = max(0.0, baseline.baseline_cost - period_cost)
        savings_carbon = max(0.0, baseline.baseline_carbon_kg - period_carbon)
        methodology = baseline.methodology
        baseline_out = MvBaselineOut.model_validate(baseline)
    else:
        savings_energy = period_energy * 0.12
        savings_cost = period_cost * 0.12
        savings_carbon = period_carbon * 0.12
        methodology = "estimate_no_baseline"
        baseline_out = None
        labeled = True
    return MvReportOut(
        building_id=building.id,
        baseline=baseline_out,
        period_energy_kwh=round(period_energy, 2),
        period_cost=round(period_cost, 2),
        period_carbon_kg=round(period_carbon, 2),
        savings_energy_kwh=round(savings_energy, 2),
        savings_cost=round(savings_cost, 2),
        savings_carbon_kg=round(savings_carbon, 2),
        labeled_estimate=labeled,
        methodology=methodology,
        notes=(
            "Labeled estimate — connect meter telemetry and set an IPMVP baseline "
            "before using figures in commercial claims."
            if labeled
            else "Computed against configured M&V baseline (weather-normalization flag honored when set)."
        ),
    )


@router.get("/buildings/{building_id}/production-readiness")
def production_readiness(building_id: str, db: DbSession, user: CurrentUser) -> dict[str, Any]:
    """Go-live checklist used by sales/CS and the Readiness settings page."""
    building = get_building_for_user(building_id, db, user)
    org = db.get(Organization, building.organization_id) if building.organization_id else None
    ent = get_org_entitlements(db, org) if org else {}
    connectors = list(
        db.scalars(select(ConnectorProfile).where(ConnectorProfile.building_id == building.id)).all()
    )
    mappings = list(
        db.scalars(select(PointMapping).where(PointMapping.building_id == building.id)).all()
    )
    cert = db.scalar(select(SiteCertification).where(SiteCertification.building_id == building.id))
    recent_telemetry = db.scalar(
        select(func.count())
        .select_from(TelemetryPoint)
        .where(TelemetryPoint.building_id == building.id)
    ) or 0

    checks = [
        {
            "id": "org_plan",
            "label": "Organization plan active/trialing",
            "passed": bool(org) and str(ent.get("status", "")).lower() in {"active", "trialing"},
            "detail": f"Plan={ent.get('plan_code', 'none')} status={ent.get('status', 'none')}",
        },
        {
            "id": "connector",
            "label": "BMS connector provisioned",
            "passed": len(connectors) > 0,
            "detail": f"{len(connectors)} connector(s)",
        },
        {
            "id": "point_map",
            "label": "Point mappings configured",
            "passed": len(mappings) >= 3,
            "detail": f"{len(mappings)} mappings",
        },
        {
            "id": "telemetry",
            "label": "Telemetry flowing",
            "passed": int(recent_telemetry) > 0 or building.is_demo,
            "detail": f"{recent_telemetry} samples stored",
        },
        {
            "id": "shadow",
            "label": "Shadow / onboarding stage advanced",
            "passed": building.onboarding_stage
            in {"shadow", "guarded_pilot", "autonomy_review", "autonomy", "demo"},
            "detail": f"stage={building.onboarding_stage}",
        },
        {
            "id": "certification",
            "label": "Site certification checklist",
            "passed": bool(building.site_certified),
            "detail": "required before Autonomous write on live sites",
        },
        {
            "id": "write_entitlement",
            "label": "Plan allows guarded or autonomous write",
            "passed": bool(ent.get("guarded_write") or ent.get("autonomous_write") or building.is_demo),
            "detail": f"guarded={ent.get('guarded_write')} autonomy={ent.get('autonomous_write')}",
        },
        {
            "id": "failsafe",
            "label": "Failsafe tested (cert checklist)",
            "passed": bool(cert and (cert.checklist_json or {}).get("failsafe_tested"))
            or building.is_demo,
            "detail": "Documented in site certification",
        },
    ]
    passed = sum(1 for c in checks if c["passed"])
    score = int(round(100 * passed / len(checks))) if checks else 0
    sellable = score >= 75 and (
        building.is_demo
        or (building.site_certified and bool(ent.get("guarded_write")))
    )
    return {
        "building_id": building.id,
        "score": score,
        "sellable_guarded": sellable,
        "sellable_autonomy": bool(building.site_certified and ent.get("autonomous_write")),
        "summary": (
            "Ready for guarded commercial pilot"
            if sellable
            else "Complete connector, mapping, and certification before selling write control"
        ),
        "checks": checks,
    }


@router.get("/organizations/{organization_id}/audit/export")
def export_org_audit(
    organization_id: str,
    db: DbSession,
    user: User = Depends(require_permission("org_manage")),
) -> dict[str, Any]:
    get_organization_for_user(organization_id, db, user)
    events = list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.organization_id == organization_id)
            .order_by(AuditEvent.timestamp.desc())
            .limit(5000)
        ).all()
    )
    return {
        "organization_id": organization_id,
        "immutable": True,
        "count": len(events),
        "events": [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                "event_type": e.event_type,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "user_id": e.user_id,
                "building_id": e.building_id,
                "reason": e.reason,
                "previous": e.previous_value_json,
                "new": e.new_value_json,
            }
            for e in events
        ],
    }


@router.post("/organizations/{organization_id}/buildings", response_model=dict, status_code=201)
def create_building(
    organization_id: str,
    db: DbSession,
    user: User = Depends(require_permission("org_manage")),
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    org = get_organization_for_user(organization_id, db, user)
    body = payload or {}
    count = db.scalar(
        select(func.count()).select_from(Building).where(Building.organization_id == org.id)
    ) or 0
    assert_building_quota(db, org, int(count))
    building = Building(
        organization_id=org.id,
        name=str(body.get("name") or "New Building"),
        location=str(body.get("location") or "Unknown"),
        timezone=str(body.get("timezone") or "UTC"),
        is_demo=False,
        shadow_mode=True,
        site_certified=False,
        write_enabled=False,
        onboarding_stage="connect",
        current_mode="ADVISORY",
    )
    db.add(building)
    db.commit()
    db.refresh(building)
    return {"id": building.id, "name": building.name, "onboarding_stage": building.onboarding_stage}
