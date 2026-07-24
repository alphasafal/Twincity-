"""Development seed data — demo credentials are for DEMO_MODE only."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import (
    Building,
    ComfortPolicy,
    ConstraintPolicy,
    GoalProfile,
    Sensor,
    User,
    Zone,
)
from app.models.enums import UserRole

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
    existing = db.scalar(select(Building).limit(1))
    if existing:
        return existing

    for item in DEMO_USERS:
        db.add(
            User(
                name=item["name"],
                email=item["email"],
                password_hash=hash_password(item["password"]),
                role=item["role"],
                is_active=True,
                last_login_at=None,
            )
        )

    building = Building(
        name="TwinPilot Demo Office",
        location="Bengaluru, IN",
        timezone="Asia/Kolkata",
        area_m2=1560.0,
        building_type="commercial_office",
        current_mode="AUTONOMOUS",
        is_demo=True,
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
                    last_seen_at=datetime.now(timezone.utc),
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
    db.commit()
    db.refresh(building)
    return building
