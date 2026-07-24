"""Safety Shield — independent of UI and LLM agent code."""

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
    minimum_ventilation: float = 0.3
    maximum_control_duration: int = 240
    minimum_confidence_for_autonomy: float = 0.85
    maximum_data_age_seconds: int = 300
    max_violation_minutes: float = 15.0


class ProposedAction(BaseModel):
    action_type: str
    zone_id: str | None = None
    current_value: float | None = None
    proposed_value: float | None = None
    duration_minutes: int = 60
    outdoor_air_fraction: float | None = None


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


class SafetyShield:
    """Validate every proposed action before execution."""

    def validate(
        self,
        action: ProposedAction,
        context: ValidationContext,
        *,
        validation_token: str | None = None,
    ) -> SafetyResult:
        checks: list[SafetyCheck] = []
        blocking: list[str] = []
        limits = context.limits

        def add(name: str, passed: bool, message: str, block_msg: str | None = None) -> None:
            checks.append(SafetyCheck(name=name, passed=passed, message=message))
            if not passed and block_msg:
                blocking.append(block_msg)

        # 1. Finite value
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

        # 2. Building limits / setpoint range
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

        # 6. Sensor health
        add(
            "sensor_health",
            context.required_sensors_healthy,
            "Required sensors are healthy"
            if context.required_sensors_healthy
            else "Required sensors are unhealthy",
            None if context.required_sensors_healthy else "Required sensors are not healthy",
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

        valid = all(c.passed for c in checks)
        recommended = None
        if not valid:
            if context.critical_alert_blocking or not context.simulation_ok:
                recommended = OperatingMode.FALLBACK
            elif not context.required_sensors_healthy or not fresh:
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
    *,
    secret: str | None = None,
    nonce: str | None = None,
    ttl_seconds: int = 900,
) -> str:
    """Build a validation token.

    v2 (HMAC): ``v2:plan_id:state_hash:actor:ts:nonce:exp:sig``
    v1 (legacy/demo): ``v1:plan_id:state_hash:actor:ts`` when secret is None.
    """
    import hashlib
    import hmac
    import secrets as _secrets

    ts_dt = timestamp or datetime.now(timezone.utc)
    ts = ts_dt.isoformat()
    if secret is None:
        return f"v1:{plan_id}:{state_hash}:{actor}:{ts}"
    nonce_val = nonce or _secrets.token_hex(8)
    exp = int(ts_dt.timestamp()) + int(ttl_seconds)
    payload = f"{plan_id}:{state_hash}:{actor}:{ts}:{nonce_val}:{exp}"
    sig = hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"v2:{plan_id}:{state_hash}:{actor}:{ts}:{nonce_val}:{exp}:{sig}"


def parse_validation_token(token: str, *, secret: str | None = None) -> dict[str, Any]:
    import hashlib
    import hmac

    parts = token.split(":")
    if not parts:
        raise ValueError("Invalid validation token")
    version = parts[0]
    if version == "v1":
        if len(parts) < 5:
            raise ValueError("Invalid validation token")
        return {
            "version": version,
            "plan_id": parts[1],
            "state_hash": parts[2],
            "actor": parts[3],
            "timestamp": ":".join(parts[4:]),
            "nonce": None,
            "exp": None,
            "signed": False,
        }
    if version == "v2":
        # v2:plan_id:state_hash:actor:ts:nonce:exp:sig
        # timestamp may contain colons (ISO), so parse from the right
        if len(parts) < 8:
            raise ValueError("Invalid validation token")
        sig = parts[-1]
        exp_s = parts[-2]
        nonce = parts[-3]
        plan_id = parts[1]
        state_hash = parts[2]
        actor = parts[3]
        ts = ":".join(parts[4:-3])
        payload = f"{plan_id}:{state_hash}:{actor}:{ts}:{nonce}:{exp_s}"
        if secret:
            expected = hmac.new(
                secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(expected, sig):
                raise ValueError("Invalid validation token signature")
            if int(exp_s) < int(datetime.now(timezone.utc).timestamp()):
                raise ValueError("Validation token expired")
        return {
            "version": version,
            "plan_id": plan_id,
            "state_hash": state_hash,
            "actor": actor,
            "timestamp": ts,
            "nonce": nonce,
            "exp": int(exp_s),
            "signed": True,
            "signature": sig,
        }
    raise ValueError("Invalid validation token")


def verify_validation_token(
    token: str,
    *,
    plan_id: str,
    state_hash: str | None = None,
    secret: str | None = None,
) -> dict[str, Any]:
    parsed = parse_validation_token(token, secret=secret)
    if parsed["plan_id"] != plan_id:
        raise ValueError("Token plan_id mismatch")
    if state_hash is not None and parsed["state_hash"] != state_hash:
        raise ValueError("Token state_hash mismatch")
    return parsed
