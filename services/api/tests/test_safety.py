"""Safety Shield regression tests."""

from __future__ import annotations

from twinpilot_optimizer.modes import OperatingMode
from twinpilot_optimizer.safety import (
    ConstraintLimits,
    ProposedAction,
    SafetyShield,
    ValidationContext,
)


def test_rejects_out_of_range_temperature():
    shield = SafetyShield()
    result = shield.validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=23.0,
            proposed_value=35.0,
            duration_minutes=60,
        ),
        ValidationContext(mode=OperatingMode.AUTONOMOUS, confidence=0.95),
    )
    assert result.valid is False
    assert any(c.name == "setpoint_range" and not c.passed for c in result.checks)


def test_rejects_excessive_setpoint_movement():
    shield = SafetyShield()
    result = shield.validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=23.0,
            proposed_value=25.5,
            duration_minutes=60,
        ),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            limits=ConstraintLimits(max_setpoint_change_per_interval=1.0),
        ),
    )
    assert result.valid is False
    assert "exceeds maximum" in " ".join(result.blocking_reasons)


def test_rejects_expired_plan():
    shield = SafetyShield()
    result = shield.validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=23.0,
            proposed_value=23.5,
            duration_minutes=60,
        ),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            plan_expired=True,
        ),
    )
    assert result.valid is False
    assert any(c.name == "plan_expiry" and not c.passed for c in result.checks)


def test_rejects_stale_state_snapshot():
    shield = SafetyShield()
    result = shield.validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=23.0,
            proposed_value=23.5,
            duration_minutes=60,
        ),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            state_snapshot_matches=False,
        ),
    )
    assert result.valid is False


def test_rejects_during_critical_fault():
    shield = SafetyShield()
    result = shield.validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=23.0,
            proposed_value=23.5,
            duration_minutes=60,
        ),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            critical_alert_blocking=True,
        ),
    )
    assert result.valid is False
    assert result.risk_level.value == "CRITICAL"


def test_rejects_low_confidence_autonomous():
    shield = SafetyShield()
    result = shield.validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=23.0,
            proposed_value=23.4,
            duration_minutes=60,
        ),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.5,
            limits=ConstraintLimits(minimum_confidence_for_autonomy=0.85),
        ),
    )
    assert result.valid is False


def test_rejects_when_simulation_fails():
    shield = SafetyShield()
    result = shield.validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=23.0,
            proposed_value=23.4,
            duration_minutes=60,
        ),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            simulation_ok=False,
        ),
    )
    assert result.valid is False


def test_advisory_requires_approval():
    shield = SafetyShield()
    result = shield.validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=23.0,
            proposed_value=23.4,
            duration_minutes=60,
        ),
        ValidationContext(
            mode=OperatingMode.ADVISORY,
            confidence=0.7,
            approval_required=True,
            approved=False,
        ),
    )
    assert result.valid is False


def test_approves_valid_low_risk_action():
    shield = SafetyShield()
    result = shield.validate(
        ProposedAction(
            action_type="cooling_setpoint",
            current_value=23.0,
            proposed_value=23.4,
            duration_minutes=60,
        ),
        ValidationContext(
            mode=OperatingMode.AUTONOMOUS,
            confidence=0.95,
            required_sensors_healthy=True,
            simulation_ok=True,
            state_snapshot_matches=True,
        ),
        validation_token="v1:plan:hash:system:ts",
    )
    assert result.valid is True
    assert result.validation_token is not None
