"""Safe actuation path: connector write + read-back ack + fail-safe."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    Alert,
    Building,
    ConnectorProfile,
    PointMapping,
    WriteAcknowledgement,
)
from twinpilot_connectors import get_adapter
from twinpilot_connectors.base import WriteRequest
from twinpilot_simulator.base import ControlActionInput


def connector_for_building(db: Session, building: Building):
    if not building.connector_profile_id:
        return None, None
    profile = db.get(ConnectorProfile, building.connector_profile_id)
    if profile is None:
        return None, None
    adapter = get_adapter(profile.adapter_type, profile.config_json or {})
    return profile, adapter


def apply_plan_actions_with_ack(
    db: Session,
    *,
    building: Building,
    plan_id: str,
    decision_id: str | None,
    actions: list[dict[str, Any]],
    zone_key: dict[str, str],
    simulator_apply,
) -> dict[str, Any]:
    """Apply actions via connector when available; always require write-ack semantics.

    For demo/mock buildings without a live BMS, falls back to simulator apply but
    still records WriteAcknowledgement rows.
    """
    settings = get_settings()
    profile, adapter = connector_for_building(db, building)
    acks: list[dict[str, Any]] = []
    all_ok = True

    # Shadow mode: recommend only — no writes
    if building.shadow_mode:
        return {
            "applied": False,
            "shadow_mode": True,
            "acks": [],
            "detail": "Shadow mode — actions not written",
        }

    if not building.write_enabled and not building.is_demo:
        return {
            "applied": False,
            "shadow_mode": False,
            "acks": [],
            "detail": "Write disabled for building",
        }

    # Fail-safe if connector reports offline
    if adapter is not None:
        health = adapter.health()
        if health.get("status") == "offline":
            building.current_mode = "FALLBACK"
            db.add(
                Alert(
                    building_id=building.id,
                    severity="CRITICAL",
                    alert_type="connector_offline",
                    title="Connector offline — FALLBACK",
                    message="BMS connector unreachable; writes blocked and mode set to FALLBACK.",
                    status="OPEN",
                )
            )
            db.flush()
            return {
                "applied": False,
                "fallback": True,
                "acks": [],
                "detail": "Connector offline",
            }

    for action in actions:
        zone_id = action.get("zone_id")
        value = action.get("proposed_value")
        if value is None:
            continue
        mapping = None
        if zone_id:
            mapping = (
                db.query(PointMapping)
                .filter(
                    PointMapping.building_id == building.id,
                    PointMapping.zone_id == zone_id,
                    PointMapping.twinpilot_metric == "cooling_setpoint",
                    PointMapping.enabled.is_(True),
                )
                .first()
            )

        readback = None
        success = False
        detail = ""
        if adapter is not None and mapping is not None and mapping.direction in {"write", "readwrite"}:
            result = adapter.write(
                WriteRequest(
                    external_point_id=mapping.external_point_id,
                    value=float(value),
                    deadband=float(mapping.deadband or 0.1),
                    unit=mapping.unit or "°C",
                )
            )
            success = bool(result.success and result.acked)
            readback = result.readback_value
            detail = result.detail
        else:
            # Simulator path (demo / no mapped write point)
            key = zone_key.get(zone_id or "", zone_id or "core")
            simulator_apply(
                ControlActionInput(
                    zone_id=key,
                    action_type=action.get("action_type", "cooling_setpoint"),
                    value=float(value),
                    duration_minutes=int(action.get("duration_minutes") or 60),
                )
            )
            readback = float(value)
            success = True
            detail = "simulator apply ack"

        ack = WriteAcknowledgement(
            building_id=building.id,
            plan_id=plan_id,
            decision_id=decision_id,
            point_mapping_id=mapping.id if mapping else None,
            requested_value=float(value),
            readback_value=readback,
            success=success,
            detail_json={"detail": detail, "zone_id": zone_id},
        )
        db.add(ack)
        acks.append(
            {
                "zone_id": zone_id,
                "requested": float(value),
                "readback": readback,
                "success": success,
                "detail": detail,
            }
        )
        if not success:
            all_ok = False

    if not all_ok and not building.is_demo:
        building.current_mode = "FALLBACK"
        db.add(
            Alert(
                building_id=building.id,
                severity="HIGH",
                alert_type="write_ack_failed",
                title="Write acknowledgement failed",
                message="One or more BMS writes failed read-back; entered FALLBACK.",
                status="OPEN",
            )
        )

    if profile is not None:
        profile.last_seen_at = datetime.now(UTC)
        profile.status = "CONNECTED" if all_ok else "DEGRADED"

    return {
        "applied": all_ok,
        "shadow_mode": False,
        "acks": acks,
        "detail": "ok" if all_ok else "partial_failure",
        "signed_tokens_required": not settings.demo_mode,
    }
