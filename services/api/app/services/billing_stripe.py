"""Stripe billing helpers — graceful when Stripe is not configured."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import EntitlementSnapshot, Organization, Subscription
from app.services.entitlements import entitlements_for_plan

PLAN_PRICE_ATTR = {
    "starter": "stripe_price_starter",
    "optimize": "stripe_price_optimize",
    "autonomy": "stripe_price_autonomy",
    "enterprise": "stripe_price_enterprise",
}


def stripe_configured() -> bool:
    return bool(get_settings().stripe_secret_key)


def ensure_subscription(db: Session, org: Organization) -> Subscription:
    sub = (
        db.query(Subscription)
        .filter(Subscription.organization_id == org.id)
        .one_or_none()
    )
    if sub:
        return sub
    entitlements = entitlements_for_plan(org.plan_code or "starter")
    sub = Subscription(
        organization_id=org.id,
        plan_code=org.plan_code or "starter",
        status="trialing",
        current_period_end=datetime.now(UTC) + timedelta(days=14),
        entitlements_json=entitlements,
    )
    db.add(sub)
    db.flush()
    return sub


def apply_plan(
    db: Session,
    org: Organization,
    plan_code: str,
    *,
    source: str,
    stripe_subscription_id: str | None = None,
    status: str = "active",
) -> Subscription:
    entitlements = entitlements_for_plan(plan_code)
    sub = ensure_subscription(db, org)
    sub.plan_code = plan_code
    sub.status = status
    sub.entitlements_json = entitlements
    sub.stripe_subscription_id = stripe_subscription_id or sub.stripe_subscription_id
    sub.current_period_end = datetime.now(UTC) + timedelta(days=30)
    org.plan_code = plan_code
    db.add(
        EntitlementSnapshot(
            organization_id=org.id,
            plan_code=plan_code,
            entitlements_json=entitlements,
            source=source,
        )
    )
    db.flush()
    return sub


def create_checkout_session(org: Organization, plan_code: str) -> dict[str, Any]:
    settings = get_settings()
    if plan_code not in PLAN_PRICE_ATTR:
        raise HTTPException(400, f"Unknown plan: {plan_code}")

    if not stripe_configured():
        # Local/dev fallback: return a synthetic checkout URL the UI can treat as mock
        return {
            "mode": "mock",
            "checkout_url": f"{settings.billing_success_url}&plan={plan_code}&org={org.id}",
            "session_id": f"mock_cs_{org.id}_{plan_code}",
            "message": "Stripe not configured — use mock checkout / direct plan apply in demo",
        }

    try:
        import stripe  # type: ignore
    except ImportError as exc:
        raise HTTPException(500, "stripe package not installed") from exc

    stripe.api_key = settings.stripe_secret_key
    price_id = getattr(settings, PLAN_PRICE_ATTR[plan_code])
    if not price_id:
        raise HTTPException(400, f"Stripe price not configured for plan {plan_code}")

    customer = org.stripe_customer_id
    if not customer:
        customer_obj = stripe.Customer.create(name=org.name, metadata={"organization_id": org.id})
        customer = customer_obj["id"]
        org.stripe_customer_id = customer

    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer,
        line_items=[{"price": price_id, "quantity": 1}],
        success_url=settings.billing_success_url,
        cancel_url=settings.billing_cancel_url,
        metadata={"organization_id": org.id, "plan_code": plan_code},
    )
    return {
        "mode": "stripe",
        "checkout_url": session["url"],
        "session_id": session["id"],
    }


def create_portal_session(org: Organization) -> dict[str, Any]:
    settings = get_settings()
    if not stripe_configured() or not org.stripe_customer_id:
        return {
            "mode": "mock",
            "portal_url": settings.billing_success_url,
            "message": "Stripe portal unavailable — configure STRIPE_SECRET_KEY",
        }
    try:
        import stripe  # type: ignore
    except ImportError as exc:
        raise HTTPException(500, "stripe package not installed") from exc
    stripe.api_key = settings.stripe_secret_key
    session = stripe.billing_portal.Session.create(
        customer=org.stripe_customer_id,
        return_url=settings.web_origin + "/settings/billing",
    )
    return {"mode": "stripe", "portal_url": session["url"]}


def handle_webhook(db: Session, payload: bytes, signature: str | None) -> dict[str, Any]:
    settings = get_settings()
    if not stripe_configured():
        return {"received": True, "mode": "ignored_no_stripe"}

    try:
        import stripe  # type: ignore
    except ImportError as exc:
        raise HTTPException(500, "stripe package not installed") from exc

    stripe.api_key = settings.stripe_secret_key
    if settings.stripe_webhook_secret:
        event = stripe.Webhook.construct_event(
            payload, signature or "", settings.stripe_webhook_secret
        )
    else:
        import json

        event = json.loads(payload.decode("utf-8"))

    event_type = event["type"] if isinstance(event, dict) else event.type
    data = event["data"]["object"] if isinstance(event, dict) else event.data.object
    metadata = data.get("metadata") or {}
    org_id = metadata.get("organization_id")
    plan_code = metadata.get("plan_code") or "starter"
    if org_id and event_type in {"checkout.session.completed", "customer.subscription.updated"}:
        org = db.get(Organization, org_id)
        if org:
            apply_plan(
                db,
                org,
                plan_code,
                source=f"stripe:{event_type}",
                stripe_subscription_id=data.get("subscription") or data.get("id"),
                status="active",
            )
            db.commit()
    return {"received": True, "type": event_type}
