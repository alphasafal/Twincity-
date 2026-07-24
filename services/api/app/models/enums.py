"""Shared domain enums."""

from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    ADMINISTRATOR = "ADMINISTRATOR"
    FACILITY_MANAGER = "FACILITY_MANAGER"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class OperatingMode(str, enum.Enum):
    AUTONOMOUS = "AUTONOMOUS"
    GUARDED = "GUARDED"
    ADVISORY = "ADVISORY"
    FALLBACK = "FALLBACK"
    MANUAL = "MANUAL"


class AlertSeverity(str, enum.Enum):
    INFORMATIONAL = "INFORMATIONAL"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(str, enum.Enum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class PlanStatus(str, enum.Enum):
    CANDIDATE = "CANDIDATE"
    SIMULATED = "SIMULATED"
    VALIDATED = "VALIDATED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    APPLIED = "APPLIED"
    EXPIRED = "EXPIRED"


class DecisionExecutionStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPLIED = "APPLIED"
    REJECTED = "REJECTED"
    ROLLED_BACK = "ROLLED_BACK"
    MANUAL = "MANUAL"
