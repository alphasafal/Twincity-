"""Self-serve signup smoke test."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_signup_creates_org_and_returns_tokens():
    client = TestClient(app)
    email = f"buyer_{uuid.uuid4().hex[:10]}@example.com"
    res = client.post(
        "/api/v1/auth/signup",
        json={
            "organization_name": "Buyer Facilities LLC",
            "name": "Casey Buyer",
            "email": email,
            "password": "Sellable-Trial-Pass1!",
            "building_name": "Tower A",
            "location": "Austin, TX",
            "plan_code": "optimize",
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["access_token"]
    assert data["organization"]["plan_code"] == "optimize"
    assert data["building"]["onboarding_stage"] == "connect"
    assert data["user"]["email"] == email

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert me.status_code == 200
    buildings = client.get(
        "/api/v1/buildings",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert buildings.status_code == 200
    assert len(buildings.json()) >= 1
    building_id = buildings.json()[0]["id"]
    ready = client.get(
        f"/api/v1/buildings/{building_id}/production-readiness",
        headers={"Authorization": f"Bearer {data['access_token']}"},
    )
    assert ready.status_code == 200
    assert "score" in ready.json()
