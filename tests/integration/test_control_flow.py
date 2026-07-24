"""Integration smoke: login → status → optimize → validate.

Uses FastAPI TestClient by default (no external server).
Set TWINPILOT_API_URL to hit a live API instead.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

API_ROOT = Path(__file__).resolve().parents[2] / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

LIVE_URL = os.getenv("TWINPILOT_API_URL", "").rstrip("/")
MANAGER_EMAIL = "manager@twinpilot.demo"
MANAGER_PASSWORD = "TwinPilot-Manager-Demo!"


class _HttpClient:
    def __init__(self, base: str):
        import httpx

        self._client = httpx.Client(base_url=base, timeout=30.0)

    def request(self, method: str, path: str, **kwargs):
        return self._client.request(method, path, **kwargs)

    def close(self) -> None:
        self._client.close()


@pytest.fixture(scope="module")
def client():
    if LIVE_URL:
        c = _HttpClient(LIVE_URL)
        yield c
        c.close()
        return

    # Prefer in-process TestClient so CI does not need a running server
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


def _auth_headers(client) -> dict[str, str]:
    res = client.request(
        "POST",
        "/api/v1/auth/login",
        json={"email": MANAGER_EMAIL, "password": MANAGER_PASSWORD},
    )
    assert res.status_code == 200, res.text
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    res = client.request("GET", "/health")
    assert res.status_code == 200
    body = res.json()
    assert body.get("status") == "ok"
    assert body.get("service") == "api"


def test_control_flow_login_status_optimize_validate(client):
    headers = _auth_headers(client)

    buildings = client.request("GET", "/api/v1/buildings", headers=headers)
    assert buildings.status_code == 200
    items = buildings.json()
    assert items, "expected seeded building"
    building_id = items[0]["id"]

    status = client.request("GET", f"/api/v1/buildings/{building_id}/status", headers=headers)
    assert status.status_code == 200
    status_body = status.json()
    assert status_body.get("simulated") is True
    assert "mode" in status_body

    gen = client.request(
        "POST",
        f"/api/v1/buildings/{building_id}/optimization/generate",
        headers=headers,
        json={
            "energy_weight": 0.25,
            "cost_weight": 0.2,
            "carbon_weight": 0.2,
            "comfort_weight": 0.2,
            "peak_weight": 0.1,
            "equipment_weight": 0.05,
        },
    )
    assert gen.status_code == 200, gen.text
    plans = gen.json().get("plans") or []
    assert plans, "expected at least one candidate plan"
    plan_id = plans[0]["id"]

    # Simulate when permission allows (manager has simulation_run)
    sim = client.request("POST", f"/api/v1/control-plans/{plan_id}/simulate", headers=headers)
    assert sim.status_code in {200, 503}, sim.text

    val = client.request("POST", f"/api/v1/control-plans/{plan_id}/validate", headers=headers)
    assert val.status_code == 200, val.text
    result = val.json()
    assert "valid" in result
    assert "checks" in result
