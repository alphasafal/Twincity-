"""Development seed data — demo credentials are for DEMO_MODE only."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import (
    Building,
    ComfortPolicy,
    ConnectorProfile,
    ConstraintPolicy,
    GoalProfile,
    Membership,
    Organization,
    PointMapping,
    Sensor,
    SiteCertification,
    Subscription,
    User,
    Zone,
)
from app.models.enums import UserRole
from app.services.entitlements import entitlements_for_plan

# Documented in README / .env.example — development only
DEMO_USERS = [
    {
        "name": "Ada Admin",
        "email": "admin@twinpilot.demo",
        "password": "TwinPilot-Admin-Demo!",
        "role": UserRole.ADMINISTRATOR.value,
    },
    {
        "name": "Morgan Manager",
        "email": "manager@twinpilot.demo",
        "password": "TwinPilot-Manager-Demo!",
        "role": UserRole.FACILITY_MANAGER.value,
    },
    {
        "name": "Omar Operator",
        "email": "operator@twinpilot.demo",
        "password": "TwinPilot-Operator-Demo!",
        "role": UserRole.OPERATOR.value,
    },
    {
        "name": "Vera Viewer",
        "email": "viewer@twinpilot.demo",
        "password": "TwinPilot-Viewer-Demo!",
        "role": UserRole.VIEWER.value,
    },
]

ZONE_DEFS = [
    ("core", "Core Office", 450.0, 60, 23.0),
    ("north", "North Office", 280.0, 30, 23.5),
    ("south", "South Office", 300.0, 40, 24.0),
    ("east", "East Office", 260.0, 30, 23.5),
    ("west", "West Office", 270.0, 35, 24.0),
]


def seed_database(db: Session) -> Building:
    settings = get_settings()
    existing = db.scalar(select(Building).limit(1))
    if existing:
        # Ensure memberships exist for older DBs upgraded in-place
        _ensure_demo_tenancy(db, existing)
        return existing

    if settings.is_production and not settings.demo_mode:
        raise RuntimeError("Refusing to seed demo data when APP_ENV=production and DEMO_MODE=false")

    org = Organization(
        name="TwinPilot Demo Org",
        slug="twinpilot-demo",
        plan_code="demo",
        is_demo=True,
    )
    db.add(org)
    db.flush()

    users: list[User] = []
    for item in DEMO_USERS:
        user = User(
            name=item["name"],
            email=item["email"],
            password_hash=hash_password(item["password"]),
            role=item["role"],
            is_active=True,
            last_login_at=None,
            default_organization_id=org.id,
        )
        db.add(user)
        users.append(user)
    db.flush()

    for user in users:
        db.add(
            Membership(
                organization_id=org.id,
                user_id=user.id,
                org_role=user.role,
                is_active=True,
            )
        )

    entitlements = entitlements_for_plan("demo")
    db.add(
        Subscription(
            organization_id=org.id,
            plan_code="demo",
            status="active",
            current_period_end=datetime.now(UTC) + timedelta(days=365),
            entitlements_json=entitlements,
        )
    )

    building = Building(
        organization_id=org.id,
        name="TwinPilot Demo Office",
        location="Bengaluru, IN",
        timezone="Asia/Kolkata",
        area_m2=1560.0,
        building_type="commercial_office",
        current_mode="AUTONOMOUS",
        is_demo=True,
        shadow_mode=False,
        site_certified=True,
        write_enabled=True,
        onboarding_stage="autonomy",
        confidence=0.91,
        autonomy_confidence_json={
            "score": 0.91,
            "sensor_health": 0.96,
            "data_freshness": 0.97,
            "forecast_confidence": 0.90,
            "simulation_confidence": 0.92,
            "model_accuracy": 0.88,
            "service_health": 0.95,
        },
    )
    db.add(building)
    db.flush()

    connector = ConnectorProfile(
        organization_id=org.id,
        building_id=building.id,
        adapter_type="mock",
        name="Demo Mock Twin",
        config_json={"provider": "mock"},
        status="CONNECTED",
        last_health_json={"status": "ok", "provider": "mock"},
        last_seen_at=datetime.now(UTC),
    )
    db.add(connector)
    db.flush()
    building.connector_profile_id = connector.id

    zone_ids: dict[str, str] = {}
    for key, name, area, capacity, preferred in ZONE_DEFS:
        zone = Zone(
            building_id=building.id,
            name=name,
            floor=1,
            area_m2=area,
            capacity=capacity,
            preferred_temperature=preferred,
            minimum_temperature=20.0,
            maximum_temperature=27.0,
            external_key=key,
        )
        db.add(zone)
        db.flush()
        zone_ids[key] = zone.id
        for sensor_type, unit in [
            ("temperature", "°C"),
            ("humidity", "%"),
            ("co2", "ppm"),
            ("occupancy", "count"),
            ("power", "kW"),
        ]:
            db.add(
                Sensor(
                    zone_id=zone.id,
                    sensor_type=sensor_type,
                    external_identifier=f"{key}.{sensor_type}",
                    unit=unit,
                    health_status="HEALTHY",
                    confidence=0.95,
                    last_seen_at=datetime.now(UTC),
                )
            )
            db.add(
                PointMapping(
                    building_id=building.id,
                    connector_profile_id=connector.id,
                    external_point_id=f"mock://{key}/{sensor_type}",
                    external_point_name=f"{name} {sensor_type}",
                    zone_id=zone.id,
                    twinpilot_metric=sensor_type,
                    direction="read",
                    unit=unit,
                    enabled=True,
                )
            )
        # Writable cooling setpoint mapping
        db.add(
            PointMapping(
                building_id=building.id,
                connector_profile_id=connector.id,
                external_point_id=f"mock://{key}/cooling_setpoint",
                external_point_name=f"{name} cooling setpoint",
                zone_id=zone.id,
                twinpilot_metric="cooling_setpoint",
                direction="readwrite",
                unit="°C",
                deadband=0.1,
                enabled=True,
            )
        )

    db.add(
        ComfortPolicy(
            building_id=building.id,
            occupied_min_temperature=21.0,
            occupied_max_temperature=26.0,
            unoccupied_min_temperature=18.0,
            unoccupied_max_temperature=28.0,
            max_violation_minutes=15.0,
            humidity_min=30.0,
            humidity_max=65.0,
            co2_max_ppm=1000.0,
        )
    )
    db.add(
        GoalProfile(
            building_id=building.id,
            name="Balanced operations",
            energy_weight=0.25,
            cost_weight=0.20,
            carbon_weight=0.20,
            comfort_weight=0.20,
            peak_weight=0.10,
            equipment_weight=0.05,
            active=True,
        )
    )
    db.add(
        ConstraintPolicy(
            building_id=building.id,
            min_cooling_setpoint=20.0,
            max_cooling_setpoint=28.0,
            min_heating_setpoint=16.0,
            max_heating_setpoint=24.0,
            max_setpoint_change_per_interval=1.5,
            minimum_ventilation=0.3,
            maximum_control_duration=240,
            minimum_confidence_for_autonomy=0.85,
            maximum_data_age_seconds=300,
        )
    )
    db.add(
        SiteCertification(
            building_id=building.id,
            checklist_json={
                "point_map_complete": True,
                "telemetry_fresh": True,
                "shadow_mode_days": 7,
                "guarded_pilot_days": 7,
                "failsafe_tested": True,
            },
            shadow_mode_complete=True,
            guarded_pilot_complete=True,
            autonomy_approved=True,
            certified_at=datetime.now(UTC),
            certified_by_user_id=users[0].id,
            notes="Demo site pre-certified for sandbox autonomous control",
        )
    )
    db.commit()
    db.refresh(building)
    return building


def _ensure_demo_tenancy(db: Session, building: Building) -> None:
    """Backfill org/memberships when upgrading an existing SQLite demo DB."""
    if building.organization_id:
        org = db.get(Organization, building.organization_id)
    else:
        org = db.scalar(select(Organization).where(Organization.slug == "twinpilot-demo"))
        if org is None:
            org = Organization(
                name="TwinPilot Demo Org",
                slug="twinpilot-demo",
                plan_code="demo",
                is_demo=True,
            )
            db.add(org)
            db.flush()
        building.organization_id = org.id
        if not building.onboarding_stage:
            building.onboarding_stage = "demo"

    users = list(db.scalars(select(User)).all())
    for user in users:
        existing = db.scalar(
            select(Membership).where(
                Membership.organization_id == org.id,
                Membership.user_id == user.id,
            )
        )
        if existing is None:
            db.add(
                Membership(
                    organization_id=org.id,
                    user_id=user.id,
                    org_role=user.role,
                    is_active=True,
                )
            )
        if user.default_organization_id is None:
            user.default_organization_id = org.id

    sub = db.scalar(select(Subscription).where(Subscription.organization_id == org.id))
    if sub is None:
        db.add(
            Subscription(
                organization_id=org.id,
                plan_code=org.plan_code or "demo",
                status="active",
                entitlements_json=entitlements_for_plan(org.plan_code or "demo"),
            )
        )

    if building.connector_profile_id is None:
        connector = ConnectorProfile(
            organization_id=org.id,
            building_id=building.id,
            adapter_type="mock",
            name="Demo Mock Twin",
            config_json={"provider": "mock"},
            status="CONNECTED",
            last_health_json={"status": "ok", "provider": "mock"},
            last_seen_at=datetime.now(UTC),
        )
        db.add(connector)
        db.flush()
        building.connector_profile_id = connector.id

    db.commit()
