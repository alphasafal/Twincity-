"""Safety Shield — independent of UI and LLM agent code.

Used by the FastAPI / interactive mock path. The EnergyPlus experiment path uses
a parallel gate in ``twinpilot_simulator.ep_experiment.validate_setpoint_action``
with the same intent: **no LLM output reaches an actuator without deterministic checks**.

Engineers: start at ``SafetyShield.validate`` — it returns a structured
``SafetyResult`` (pass/fail, risk, blocking reasons, optional validation token).
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from twinpilot_optimizer.modes import OperatingMode, mode_allows_auto_apply


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SafetyCheck(BaseModel):
    name: str
    passed: bool
    message: str


class SafetyResult(BaseModel):
    valid: bool
    risk_level: RiskLevel
    checks: list[SafetyCheck]
    blocking_reasons: list[str]
    recommended_mode: OperatingMode | None = None
    validation_token: str | None = None


class ConstraintLimits(BaseModel):
    min_cooling_setpoint: float = 20.0
    max_cooling_setpoint: float = 28.0
    min_heating_setpoint: float = 16.0
    max_heating_setpoint: float = 24.0
    max_setpoint_change_per_interval: float = 1.5
    heating_cooling_deadband_c: float = 1.5
    minimum_ventilation: float = 0.3
    maximum_control_duration: int = 240
    minimum_confidence_for_autonomy: float = 0.85
    maximum_data_age_seconds: int = 300
    max_violation_minutes: float = 15.0
    min_sensor_temperature_c: float = 0.0
    max_sensor_temperature_c: float = 50.0


class ProposedAction(BaseModel):
    action_type: str
    zone_id: str | None = None
    current_value: float | None = None
    proposed_value: float | None = None
    duration_minutes: int = 60
    outdoor_air_fraction: float | None = None
    paired_heating_setpoint: float | None = None
    paired_cooling_setpoint: float | None = None


class ValidationContext(BaseModel):
    mode: OperatingMode = OperatingMode.ADVISORY
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    data_age_seconds: float = 0.0
    required_sensors_healthy: bool = True
    simulated_comfort_violation_minutes: float = 0.0
    critical_alert_blocking: bool = False
    equipment_cycle_ok: bool = True
    plan_expired: bool = False
    state_snapshot_matches: bool = True
    simulation_ok: bool = True
    user_has_permission: bool = True
    approval_required: bool = False
    approved: bool = False
    limits: ConstraintLimits = Field(default_factory=ConstraintLimits)
    now: datetime | None = None
    # Failure / sensor integrity signals (LLM cannot clear these)
    missing_temperature: bool = False
    missing_occupancy: bool = False
    impossible_sensor_value: bool = False
    llm_timeout: bool = False
    mcp_failure: bool = False
    energyplus_failure: bool = False
    manual_override: bool = False
    malformed_agent_response: bool = False
    invalid_action_schema: bool = False
    measured_zone_temperature: float | None = None


class SafetyShield:
    """Validate every proposed action before execution.

    Check order (high level): finite value → range → rate-of-change → deadband →
    sensor health / freshness → mode & permission → infrastructure failures
    (LLM timeout, MCP failure, EnergyPlus failure) → comfort simulation flags.
    Any blocking failure ⇒ ``valid=False``; callers must not actuate.
    """

    def validate(
        self,
        action: ProposedAction,
        context: ValidationContext,
        *,
        validation_token: str | None = None,
    ) -> SafetyResult:
        """Run all safety checks and return an auditable ``SafetyResult``.

        Args:
            action: What the agent wants to do (e.g. cooling setpoint change).
            context: Live building / session context the LLM cannot forge away
                (sensor health, mode, timeouts, manual override, etc.).
            validation_token: Optional prior token for approve/apply chains.
        """
        checks: list[SafetyCheck] = []
        blocking: list[str] = []
        limits = context.limits

        def add(name: str, passed: bool, message: str, block_msg: str | None = None) -> None:
            checks.append(SafetyCheck(name=name, passed=passed, message=message))
            if not passed and block_msg:
                blocking.append(block_msg)

        # 1. Finite value — reject NaN / Inf before any numeric comparisons
        value = action.proposed_value
        finite = value is None or (isinstance(value, (int, float)) and abs(value) != float("inf"))
        if value is not None:
            try:
                finite = finite and value == value  # NaN check
            except Exception:
                finite = False
        add(
            "finite_value",
            finite,
            "Proposed value is finite" if finite else "Proposed value is not finite",
            None if finite else "Proposed value must be a finite number",
        )

        # 2. Building limits / setpoint range (configured ConstraintLimits)
        in_range = True
        if action.action_type in {"cooling_setpoint", "request_zone_setpoint"} and value is not None:
            in_range = limits.min_cooling_setpoint <= value <= limits.max_cooling_setpoint
            add(
                "setpoint_range",
                in_range,
                "Within configured range" if in_range else "Outside configured cooling range",
                None if in_range else "Proposed cooling setpoint outside building limits",
            )
        elif action.action_type == "heating_setpoint" and value is not None:
            in_range = limits.min_heating_setpoint <= value <= limits.max_heating_setpoint
            add(
                "setpoint_range",
                in_range,
                "Within configured range" if in_range else "Outside configured heating range",
                None if in_range else "Proposed heating setpoint outside building limits",
            )
        else:
            add("setpoint_range", True, "Range check not applicable for this action type")

        # 2b. Heating / cooling deadband
        deadband_ok = True
        if (
            action.action_type in {"cooling_setpoint", "request_zone_setpoint"}
            and value is not None
            and action.paired_heating_setpoint is not None
        ):
            deadband_ok = value >= (
                action.paired_heating_setpoint + limits.heating_cooling_deadband_c
            )
            add(
                "heating_cooling_deadband",
                deadband_ok,
                "Heating/cooling deadband maintained"
                if deadband_ok
                else "Cooling setpoint too close to heating setpoint",
                None if deadband_ok else "Heating/cooling deadband would be violated",
            )
        elif (
            action.action_type == "heating_setpoint"
            and value is not None
            and action.paired_cooling_setpoint is not None
        ):
            deadband_ok = (
                action.paired_cooling_setpoint >= value + limits.heating_cooling_deadband_c
            )
            add(
                "heating_cooling_deadband",
                deadband_ok,
                "Heating/cooling deadband maintained"
                if deadband_ok
                else "Heating setpoint too close to cooling setpoint",
                None if deadband_ok else "Heating/cooling deadband would be violated",
            )
        else:
            add("heating_cooling_deadband", True, "Deadband check not applicable")

        # 3. Max movement per interval
        movement_ok = True
        if value is not None and action.current_value is not None:
            delta = abs(value - action.current_value)
            movement_ok = delta <= limits.max_setpoint_change_per_interval + 1e-9
            add(
                "max_movement",
                movement_ok,
                f"Change {delta:.2f} within limit {limits.max_setpoint_change_per_interval}",
                None
                if movement_ok
                else f"Setpoint change {delta:.2f} exceeds maximum per interval",
            )
        else:
            add("max_movement", True, "Movement check skipped (missing current/proposed)")

        # 4. Duration
        duration_ok = 1 <= action.duration_minutes <= limits.maximum_control_duration
        add(
            "duration",
            duration_ok,
            "Duration allowed" if duration_ok else "Duration outside allowed window",
            None if duration_ok else "Action duration is not allowed",
        )

        # 5. Telemetry freshness
        fresh = context.data_age_seconds <= limits.maximum_data_age_seconds
        add(
            "telemetry_freshness",
            fresh,
            "Telemetry is sufficiently fresh" if fresh else "Telemetry is stale",
            None if fresh else "Telemetry is not sufficiently fresh",
        )

        # 6. Sensor health / missing / impossible values
        sensors_ok = (
            context.required_sensors_healthy
            and not context.missing_temperature
            and not context.missing_occupancy
            and not context.impossible_sensor_value
        )
        if context.measured_zone_temperature is not None:
            t = context.measured_zone_temperature
            if t != t or abs(t) == float("inf"):  # NaN / inf
                sensors_ok = False
            elif t < limits.min_sensor_temperature_c or t > limits.max_sensor_temperature_c:
                sensors_ok = False
                context.impossible_sensor_value = True
        add(
            "sensor_health",
            sensors_ok,
            "Required sensors are healthy" if sensors_ok else "Required sensors are unhealthy",
            None if sensors_ok else "Required sensors are not healthy or values are invalid",
        )
        add(
            "missing_temperature",
            not context.missing_temperature,
            "Zone temperature present"
            if not context.missing_temperature
            else "Zone temperature missing",
            None if not context.missing_temperature else "Zone temperature is missing",
        )
        add(
            "missing_occupancy",
            not context.missing_occupancy,
            "Occupancy present" if not context.missing_occupancy else "Occupancy missing",
            None if not context.missing_occupancy else "Occupancy is missing",
        )

        # 7. Confidence vs mode
        conf_ok = True
        if context.mode == OperatingMode.AUTONOMOUS:
            conf_ok = context.confidence >= limits.minimum_confidence_for_autonomy
        elif context.mode == OperatingMode.GUARDED:
            conf_ok = context.confidence >= 0.65
        add(
            "confidence_threshold",
            conf_ok,
            f"Confidence {context.confidence:.2f} meets mode threshold"
            if conf_ok
            else f"Confidence {context.confidence:.2f} below mode threshold",
            None if conf_ok else "Confidence does not meet the current mode threshold",
        )

        # 8. Simulated comfort
        comfort_ok = context.simulated_comfort_violation_minutes <= limits.max_violation_minutes
        add(
            "comfort_prediction",
            comfort_ok,
            "Predicted comfort acceptable"
            if comfort_ok
            else f"Predicted occupied comfort violation: {context.simulated_comfort_violation_minutes:.0f} minutes",
            None
            if comfort_ok
            else "Predicted comfort violation exceeds configured maximum",
        )

        # 9. Minimum ventilation
        vent = action.outdoor_air_fraction
        vent_ok = vent is None or vent >= limits.minimum_ventilation
        add(
            "minimum_ventilation",
            vent_ok,
            "Minimum ventilation maintained" if vent_ok else "Outdoor-air fraction too low",
            None if vent_ok else "Minimum ventilation would not be maintained",
        )

        # 10. Critical alerts
        add(
            "critical_alerts",
            not context.critical_alert_blocking,
            "No critical alert blocks automation"
            if not context.critical_alert_blocking
            else "Critical alert blocks automation",
            None
            if not context.critical_alert_blocking
            else "A critical alert blocks automation",
        )

        # 11. Equipment cycling
        add(
            "equipment_cycling",
            context.equipment_cycle_ok,
            "Equipment cycling limits respected"
            if context.equipment_cycle_ok
            else "Equipment cycling limit exceeded",
            None if context.equipment_cycle_ok else "Equipment cycling limits would be violated",
        )

        # 12. Mode permission for action
        risk = self._estimate_risk(action, context, blocking)
        mode_ok = True
        if context.mode in {OperatingMode.FALLBACK, OperatingMode.MANUAL}:
            mode_ok = False
            add(
                "mode_permission",
                False,
                f"Automatic actuation not allowed in {context.mode.value}",
                f"Action is not allowed in {context.mode.value} mode",
            )
        elif context.mode == OperatingMode.ADVISORY and not context.approved:
            mode_ok = False
            add(
                "mode_permission",
                False,
                "Advisory mode requires operator approval",
                "Operator approval is required in ADVISORY mode",
            )
        elif not mode_allows_auto_apply(context.mode, risk.value) and not context.approved:
            mode_ok = False
            add(
                "mode_permission",
                False,
                f"{risk.value} risk not auto-allowed in {context.mode.value}",
                f"Risk level {risk.value} is not allowed for automatic apply in {context.mode.value}",
            )
        else:
            add("mode_permission", True, f"Action allowed in {context.mode.value}")

        # 13. User permission when approval required
        perm_ok = (not context.approval_required) or context.user_has_permission
        add(
            "user_permission",
            perm_ok,
            "User has required permission" if perm_ok else "User lacks required permission",
            None if perm_ok else "User does not have permission for this control action",
        )

        # 14. Plan expiry
        add(
            "plan_expiry",
            not context.plan_expired,
            "Plan has not expired" if not context.plan_expired else "Plan has expired",
            None if not context.plan_expired else "The plan has expired",
        )

        # 15. Simulation corresponds to current state
        state_ok = context.state_snapshot_matches and context.simulation_ok
        add(
            "state_snapshot",
            state_ok,
            "Simulation corresponds to current building state"
            if state_ok
            else "Simulation does not match current building state or failed",
            None
            if state_ok
            else "Simulation does not correspond to the current building state",
        )

        # 16. Infrastructure / agent integrity failures → emergency fallback path
        infra_ok = not (
            context.llm_timeout
            or context.mcp_failure
            or context.energyplus_failure
            or context.malformed_agent_response
            or context.invalid_action_schema
            or context.manual_override
        )
        infra_msg = "Agent/infrastructure integrity ok"
        infra_block = None
        if context.manual_override:
            infra_msg = "Manual override active — automatic actuation blocked"
            infra_block = "Manual override blocks automatic actuation"
        elif context.llm_timeout:
            infra_msg = "LLM timed out"
            infra_block = "LLM timeout — no uncontrolled action; fallback hold"
        elif context.mcp_failure:
            infra_msg = "MCP failure"
            infra_block = "MCP failure — no uncontrolled action; fallback hold"
        elif context.energyplus_failure:
            infra_msg = "EnergyPlus failure"
            infra_block = "EnergyPlus failure — actuation blocked"
        elif context.malformed_agent_response:
            infra_msg = "Malformed agent response"
            infra_block = "Malformed agent response rejected"
        elif context.invalid_action_schema:
            infra_msg = "Invalid action schema"
            infra_block = "Invalid action schema rejected"
        add("infrastructure_integrity", infra_ok, infra_msg, infra_block)

        valid = all(c.passed for c in checks)
        recommended = None
        if not valid:
            if (
                context.critical_alert_blocking
                or not context.simulation_ok
                or context.llm_timeout
                or context.mcp_failure
                or context.energyplus_failure
                or context.manual_override
            ):
                recommended = OperatingMode.FALLBACK
            elif not sensors_ok or not fresh:
                recommended = OperatingMode.GUARDED
            else:
                recommended = OperatingMode.ADVISORY

        return SafetyResult(
            valid=valid,
            risk_level=risk,
            checks=checks,
            blocking_reasons=blocking,
            recommended_mode=recommended,
            validation_token=validation_token if valid else None,
        )

    def _estimate_risk(
        self,
        action: ProposedAction,
        context: ValidationContext,
        blocking: list[str],
    ) -> RiskLevel:
        if context.critical_alert_blocking:
            return RiskLevel.CRITICAL
        if action.proposed_value is not None and action.current_value is not None:
            delta = abs(action.proposed_value - action.current_value)
            if delta > 1.0 or context.simulated_comfort_violation_minutes > 10:
                return RiskLevel.HIGH
            if delta > 0.5:
                return RiskLevel.MEDIUM
        if blocking:
            return RiskLevel.HIGH
        return RiskLevel.LOW


def build_validation_token(
    plan_id: str,
    state_hash: str,
    actor: str,
    timestamp: datetime | None = None,
) -> str:
    ts = (timestamp or datetime.now(timezone.utc)).isoformat()
    return f"v1:{plan_id}:{state_hash}:{actor}:{ts}"


def parse_validation_token(token: str) -> dict[str, Any]:
    parts = token.split(":")
    if len(parts) < 5 or parts[0] != "v1":
        raise ValueError("Invalid validation token")
    return {
        "version": parts[0],
        "plan_id": parts[1],
        "state_hash": parts[2],
        "actor": parts[3],
        "timestamp": ":".join(parts[4:]),
    }
