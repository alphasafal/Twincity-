"""Plan entitlements for TwinPilot SaaS subscriptions."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Organization, Subscription

PLAN_ENTITLEMENTS: dict[str, dict[str, Any]] = {
    "starter": {
        "max_buildings": 1,
        "autonomous_write": False,
        "guarded_write": False,
        "connector_types": ["mock", "bacnet_ip"],
        "assistant_tier": "deterministic",
        "sso": False,
        "custom_connectors": False,
        "mv_reporting": False,
        "label": "Starter",
        "description": "Read-only monitoring for one building",
    },
    "optimize": {
        "max_buildings": 5,
        "autonomous_write": False,
        "guarded_write": True,
        "connector_types": ["mock", "bacnet_ip", "modbus_tcp", "honeywell_niagara"],
        "assistant_tier": "deterministic",
        "sso": False,
        "custom_connectors": False,
        "mv_reporting": True,
        "label": "Optimize",
        "description": "Guarded write + multi-site optimization",
    },
    "autonomy": {
        "max_buildings": 25,
        "autonomous_write": True,
        "guarded_write": True,
        "connector_types": ["mock", "bacnet_ip", "modbus_tcp", "honeywell_niagara"],
        "assistant_tier": "ollama",
        "sso": False,
        "custom_connectors": False,
        "mv_reporting": True,
        "label": "Autonomy",
        "description": "Certified autonomous control for portfolios",
    },
    "enterprise": {
        "max_buildings": 1000,
        "autonomous_write": True,
        "guarded_write": True,
        "connector_types": ["mock", "bacnet_ip", "modbus_tcp", "honeywell_niagara", "custom"],
        "assistant_tier": "ollama",
        "sso": True,
        "custom_connectors": True,
        "mv_reporting": True,
        "label": "Enterprise",
        "description": "SSO, custom connectors, unlimited scale",
    },
    "demo": {
        "max_buildings": 10,
        "autonomous_write": True,
        "guarded_write": True,
        "connector_types": ["mock", "bacnet_ip", "modbus_tcp", "honeywell_niagara"],
        "assistant_tier": "deterministic",
        "sso": False,
        "custom_connectors": False,
        "mv_reporting": True,
        "label": "Demo",
        "description": "Local/sandbox entitlements",
    },
}


def entitlements_for_plan(plan_code: str) -> dict[str, Any]:
    return dict(PLAN_ENTITLEMENTS.get(plan_code, PLAN_ENTITLEMENTS["starter"]))


def get_org_entitlements(db: Session, organization: Organization) -> dict[str, Any]:
    sub = db.query(Subscription).filter(Subscription.organization_id == organization.id).one_or_none()
    if sub and sub.entitlements_json:
        base = entitlements_for_plan(sub.plan_code)
        merged = {**base, **sub.entitlements_json}
        merged["plan_code"] = sub.plan_code
        merged["status"] = sub.status
        return merged
    plan = organization.plan_code or "starter"
    ent = entitlements_for_plan(plan)
    ent["plan_code"] = plan
    ent["status"] = "active" if organization.is_demo else "trialing"
    return ent


def require_entitlement(db: Session, organization: Organization, key: str, *, expected: Any = True) -> dict[str, Any]:
    ent = get_org_entitlements(db, organization)
    value = ent.get(key)
    if expected is True and not value:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Plan entitlement required: {key}",
        )
    if expected is not True and value != expected:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Plan entitlement mismatch for {key}",
        )
    return ent


def assert_connector_allowed(db: Session, organization: Organization, adapter_type: str) -> None:
    ent = get_org_entitlements(db, organization)
    allowed = ent.get("connector_types") or []
    if adapter_type not in allowed:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Connector '{adapter_type}' not included in plan {ent.get('plan_code')}",
        )


def assert_building_quota(db: Session, organization: Organization, current_count: int) -> None:
    ent = get_org_entitlements(db, organization)
    max_buildings = int(ent.get("max_buildings") or 1)
    if current_count >= max_buildings:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Building limit reached for plan ({max_buildings})",
        )
