"""Safety + failure-mode tests — unsafe / failed recommendations must not pass."""

from __future__ import annotations

import pytest

from twinpilot_optimizer.modes import OperatingMode
from twinpilot_optimizer.safety import (
    ConstraintLimits,
    ProposedAction,
    SafetyShield,
    ValidationContext,
)


@pytest.fixture
def shield() -> SafetyShield:
    return SafetyShield()


def _cool(proposed: float = 24.0, current: float = 23.5) -> ProposedAction:
    return ProposedAction(
        action_type="cooling_setpoint",
        zone_id="SPACE1-1",
        current_value=current,
        proposed_value=proposed,
        duration_minutes=60,
        paired_heating_setpoint=22.0,
    )


def test_llm_timeout_blocks_and_recommends_fallback(shield: SafetyShield):
    result = shield.validate(
        _cool(),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            llm_timeout=True,
        ),
    )
    assert result.valid is False
    assert result.recommended_mode == OperatingMode.FALLBACK
    assert any(c.name == "infrastructure_integrity" and not c.passed for c in result.checks)


def test_mcp_failure_blocks(shield: SafetyShield):
    result = shield.validate(
        _cool(),
        ValidationContext(mode=OperatingMode.AUTONOMOUS, confidence=0.95, mcp_failure=True),
    )
    assert result.valid is False
    assert "MCP failure" in " ".join(result.blocking_reasons)


def test_energyplus_failure_blocks(shield: SafetyShield):
    result = shield.validate(
        _cool(),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS, confidence=0.95, energyplus_failure=True
        ),
    )
    assert result.valid is False
    assert result.recommended_mode == OperatingMode.FALLBACK


def test_invalid_json_malformed_response_blocks(shield: SafetyShield):
    result = shield.validate(
        _cool(),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            malformed_agent_response=True,
        ),
    )
    assert result.valid is False


def test_invalid_action_schema_blocks(shield: SafetyShield):
    result = shield.validate(
        _cool(),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            invalid_action_schema=True,
        ),
    )
    assert result.valid is False


def test_recommendation_outside_safe_range_rejected(shield: SafetyShield):
    result = shield.validate(
        _cool(proposed=32.0),
        ValidationContext(mode=OperatingMode.AUTONOMOUS, confidence=0.95),
    )
    assert result.valid is False
    assert any(c.name == "setpoint_range" and not c.passed for c in result.checks)


def test_missing_occupancy_blocks(shield: SafetyShield):
    result = shield.validate(
        _cool(),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            missing_occupancy=True,
        ),
    )
    assert result.valid is False


def test_missing_temperature_blocks(shield: SafetyShield):
    result = shield.validate(
        _cool(),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            missing_temperature=True,
        ),
    )
    assert result.valid is False


def test_impossible_sensor_temperature_blocks(shield: SafetyShield):
    result = shield.validate(
        _cool(),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            measured_zone_temperature=999.0,
        ),
    )
    assert result.valid is False


def test_stale_sensor_values_block(shield: SafetyShield):
    result = shield.validate(
        _cool(),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            data_age_seconds=10_000,
            limits=ConstraintLimits(maximum_data_age_seconds=300),
        ),
    )
    assert result.valid is False


def test_deadband_violation_rejected(shield: SafetyShield):
    result = shield.validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=23.0,
            proposed_value=22.5,
            duration_minutes=60,
            paired_heating_setpoint=22.0,
        ),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            limits=ConstraintLimits(heating_cooling_deadband_c=1.5),
        ),
    )
    assert result.valid is False
    assert any(c.name == "heating_cooling_deadband" and not c.passed for c in result.checks)


def test_manual_override_blocks_auto_actuation(shield: SafetyShield):
    result = shield.validate(
        _cool(),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            manual_override=True,
        ),
    )
    assert result.valid is False
    assert result.recommended_mode == OperatingMode.FALLBACK


def test_safe_autonomous_action_can_pass(shield: SafetyShield):
    result = shield.validate(
        _cool(proposed=24.0, current=23.5),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            required_sensors_healthy=True,
            data_age_seconds=10,
            simulation_ok=True,
            state_snapshot_matches=True,
        ),
    )
    assert result.valid is True