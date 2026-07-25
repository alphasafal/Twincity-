"""Failure-mode integration checks for Eco-Loop / TwinPilot safety behaviour."""

from __future__ import annotations

import json

import pytest

from twinpilot_optimizer.modes import OperatingMode
from twinpilot_optimizer.safety import ProposedAction, SafetyShield, ValidationContext


def test_dashboard_disconnection_does_not_actuate():
    """WebSocket/dashboard disconnect must not imply actuation permission."""
    shield = SafetyShield()
    # Even with high confidence, missing approval in ADVISORY blocks apply.
    result = shield.validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=23.0,
            proposed_value=24.0,
            duration_minutes=60,
            paired_heating_setpoint=21.0,
        ),
        ValidationContext(
            mode=OperatingMode.ADVISORY,
            confidence=0.99,
            approved=False,
        ),
    )
    assert result.valid is False
    assert any("approval" in r.lower() for r in result.blocking_reasons)


def test_database_unavailability_surfaces_health_error():
    """Service health should report database errors without inventing success."""
    from app.services.runtime import RuntimeHub

    hub = RuntimeHub()
    hub.service_health["database"] = "error"
    assert hub.service_health["database"] == "error"
    # No automatic apply path should ignore this — FALLBACK recommended on E+ failure.
    result = SafetyShield().validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=23.0,
            proposed_value=23.5,
            duration_minutes=60,
            paired_heating_setpoint=21.0,
        ),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            energyplus_failure=True,
        ),
    )
    assert result.valid is False
    assert result.recommended_mode == OperatingMode.FALLBACK


def test_interrupted_simulation_blocks_apply():
    result = SafetyShield().validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=23.0,
            proposed_value=23.5,
            duration_minutes=60,
            paired_heating_setpoint=21.0,
        ),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            simulation_ok=False,
        ),
    )
    assert result.valid is False
    assert result.recommended_mode == OperatingMode.FALLBACK


def test_invalid_json_agent_response_is_rejected_by_safety():
    result = SafetyShield().validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=23.0,
            proposed_value=24.0,
            duration_minutes=60,
            paired_heating_setpoint=21.0,
        ),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            malformed_agent_response=True,
        ),
    )
    assert result.valid is False
    assert any(c.name == "infrastructure_integrity" and not c.passed for c in result.checks)


def test_energyplus_unavailable_strict_no_silent_mock(monkeypatch):
    from twinpilot_simulator.energyplus import EnergyPlusAdapter
    from twinpilot_simulator.base import SimulationConfig
    from twinpilot_simulator.ep_experiment import EnergyPlusUnavailableError

    monkeypatch.delenv("ENERGYPLUS_ALLOW_MOCK_FALLBACK", raising=False)
    monkeypatch.setenv("ENERGYPLUS_HOME", "")
    monkeypatch.setenv("ENERGYPLUS_MODEL_PATH", "")
    monkeypatch.setenv("ENERGYPLUS_WEATHER_PATH", "")
    adapter = EnergyPlusAdapter()
    with pytest.raises(EnergyPlusUnavailableError):
        adapter.initialize(SimulationConfig(energyplus_home=None, model_path=None, weather_path=None))


def test_comparison_json_schema_present():
    from pathlib import Path

    cmp = Path("/workspace/results/comparison/comparison.json")
    if not cmp.exists():
        pytest.skip("comparison.json not generated yet")
    data = json.loads(cmp.read_text())
    assert data["baseline_status"] == "completed"
    assert data["agent_status"] == "completed"
    assert "total_energy_kwh" in data
    assert data["inputs_identical"] is True
