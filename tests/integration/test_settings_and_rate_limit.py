"""Settings write APIs and auth rate limiting."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

API_ROOT = Path(__file__).resolve().parents[2] / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.core.rate_limit import limiter  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def client():
    # Reset limiter between tests
    limiter._hits.clear()  # noqa: SLF001
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_admin_can_update_constraints_and_building(client: TestClient):
    admin = _login(client, "admin@twinpilot.demo", "TwinPilot-Admin-Demo!")
    building_id = client.get("/api/v1/buildings", headers=admin).json()[0]["id"]

    patched = client.patch(
        f"/api/v1/buildings/{building_id}/constraints",
        headers=admin,
        json={
            "max_setpoint_change_per_interval": 1.2,
            "reason": "Tighten movement for test",
        },
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["max_setpoint_change_per_interval"] == 1.2

    building = client.patch(
        f"/api/v1/buildings/{building_id}",
        headers=admin,
        json={"name": "TwinPilot Demo Office Updated", "reason": "Rename for test"},
    )
    assert building.status_code == 200, building.text
    assert building.json()["name"] == "TwinPilot Demo Office Updated"


def test_admin_can_invite_user(client: TestClient):
    admin = _login(client, "admin@twinpilot.demo", "TwinPilot-Admin-Demo!")
    created = client.post(
        "/api/v1/users",
        headers=admin,
        json={
            "name": "Replay Tester",
            "email": "replay.tester@twinpilot.demo",
            "password": "TwinPilot-Replay-Demo!",
            "role": "OPERATOR",
            "reason": "Integration invite",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["role"] == "OPERATOR"

    # Viewer cannot invite
    viewer = _login(client, "viewer@twinpilot.demo", "TwinPilot-Viewer-Demo!")
    denied = client.post(
        "/api/v1/users",
        headers=viewer,
        json={
            "name": "Nope",
            "email": "nope@twinpilot.demo",
            "password": "TwinPilot-Nope-Demo!",
            "role": "VIEWER",
            "reason": "Should fail",
        },
    )
    assert denied.status_code == 403


def test_auth_rate_limit(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from app.core import config as config_mod
    from app.core import rate_limit as rl

    settings = config_mod.get_settings()
    monkeypatch.setattr(settings, "rate_limit_auth_per_minute", 3)
    limiter._hits.clear()  # noqa: SLF001

    statuses = []
    for _ in range(8):
        res = client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@twinpilot.demo", "password": "wrong-password-xx"},
        )
        statuses.append(res.status_code)
    assert 429 in statuses
    assert rl.limiter._hits  # noqa: SLF001
