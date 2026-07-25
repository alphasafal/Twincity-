"""End-to-end advisory approve → apply → rollback via TestClient."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

API_ROOT = Path(__file__).resolve().parents[2] / "services" / "api"
if str(API_ROOT) not in sys.path:
    sys.path.insert(0, str(API_ROOT))

from app.main import app  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, email: str, password: str) -> dict[str, str]:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200, res.text
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


def test_advisory_approve_apply_and_rollback(client: TestClient):
    admin = _login(client, "admin@twinpilot.demo", "TwinPilot-Admin-Demo!")
    manager = _login(client, "manager@twinpilot.demo", "TwinPilot-Manager-Demo!")

    buildings = client.get("/api/v1/buildings", headers=manager)
    building_id = buildings.json()[0]["id"]

    reset = client.post("/api/v1/demo/scenarios/reset", headers=manager)
    assert reset.status_code == 200, reset.text

    mode = client.patch(
        f"/api/v1/buildings/{building_id}/mode",
        headers=admin,
        json={"mode": "ADVISORY", "reason": "Integration test advisory path"},
    )
    assert mode.status_code == 200, mode.text
    assert mode.json()["current_mode"] == "ADVISORY"

    gen = client.post(
        f"/api/v1/buildings/{building_id}/optimization/generate",
        headers=manager,
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
    plans = gen.json()["plans"]
    balanced = next(p for p in plans if p["source"] == "BALANCED")
    plan_id = balanced["id"]

    sim = client.post(f"/api/v1/control-plans/{plan_id}/simulate", headers=manager)
    assert sim.status_code == 200, sim.text
    assert sim.json()["result"]["comfort_violation_minutes"] <= 15

    val = client.post(f"/api/v1/control-plans/{plan_id}/validate", headers=manager)
    assert val.status_code == 200, val.text
    # Advisory without approval should block automatic validity
    assert val.json()["valid"] is False
    assert any("approval" in r.lower() for r in val.json().get("blocking_reasons", []))

    approve = client.post(
        f"/api/v1/control-plans/{plan_id}/approve",
        headers=manager,
        json={"reason": "Integration test approval"},
    )
    assert approve.status_code == 200, approve.text
    assert approve.json()["status"] == "APPROVED"

    apply = client.post(f"/api/v1/control-plans/{plan_id}/apply", headers=manager)
    assert apply.status_code == 200, apply.text
    assert apply.json()["status"] == "APPLIED"
    assert apply.json().get("decision_id")

    ledger = client.get(f"/api/v1/buildings/{building_id}/ledger", headers=manager)
    assert ledger.status_code == 200
    assert len(ledger.json()) >= 1

    audit = client.get(f"/api/v1/buildings/{building_id}/audit", headers=manager)
    assert audit.status_code == 200
    types = {row["event_type"] for row in audit.json()}
    assert "control_applied" in types

    rollback = client.post(
        f"/api/v1/buildings/{building_id}/rollback",
        headers=manager,
        json={"reason": "Integration test rollback", "target_safe_policy": "default_safe_policy"},
    )
    assert rollback.status_code == 200, rollback.text
    assert rollback.json()["status"] == "completed"


def test_infeasible_target_returns_safe_message(client: TestClient):
    manager = _login(client, "manager@twinpilot.demo", "TwinPilot-Manager-Demo!")
    building_id = client.get("/api/v1/buildings", headers=manager).json()[0]["id"]
    client.post("/api/v1/demo/scenarios/infeasible_target/start", headers=manager)
    gen = client.post(
        f"/api/v1/buildings/{building_id}/optimization/generate",
        headers=manager,
        json={
            "energy_weight": 0.25,
            "cost_weight": 0.2,
            "carbon_weight": 0.2,
            "comfort_weight": 0.2,
            "peak_weight": 0.1,
            "equipment_weight": 0.05,
            "energy_target_pct": 40,
            "zero_comfort_deviation": True,
            "allow_schedule_changes": False,
        },
    )
    assert gen.status_code == 200, gen.text
    plans = gen.json()["plans"]
    infeasible = [p for p in plans if not p["feasibility"]]
    assert infeasible
    reasons = " ".join(
        " ".join(p["predicted_metrics_json"].get("infeasibility_reasons") or []) for p in infeasible
    )
    assert "not feasible" in reasons.lower()
    assert "17.8" in reasons
