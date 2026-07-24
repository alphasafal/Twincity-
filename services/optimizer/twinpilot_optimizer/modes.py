"""Deterministic operating-mode state machine.

Critical safety logic must not depend on an LLM.
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable

from pydantic import BaseModel, Field


class OperatingMode(str, Enum):
    AUTONOMOUS = "AUTONOMOUS"
    GUARDED = "GUARDED"
    ADVISORY = "ADVISORY"
    FALLBACK = "FALLBACK"
    MANUAL = "MANUAL"


class ModeThresholds(BaseModel):
    autonomous: float = Field(default=0.85, ge=0.0, le=1.0)
    guarded: float = Field(default=0.65, ge=0.0, le=1.0)
    advisory: float = Field(default=0.40, ge=0.0, le=1.0)


def recommend_mode(
    confidence: float,
    *,
    critical_fault: bool = False,
    simulation_failed: bool = False,
    operator_manual: bool = False,
    thresholds: ModeThresholds | None = None,
) -> OperatingMode:
    """Recommend a mode from confidence and hard safety signals."""
    if operator_manual:
        return OperatingMode.MANUAL
    if critical_fault:
        return OperatingMode.FALLBACK
    if simulation_failed and confidence < 0.65:
        return OperatingMode.FALLBACK if confidence < 0.40 else OperatingMode.ADVISORY

    thresholds = thresholds or ModeThresholds()
    if confidence >= thresholds.autonomous:
        return OperatingMode.AUTONOMOUS
    if confidence >= thresholds.guarded:
        return OperatingMode.GUARDED
    if confidence >= thresholds.advisory:
        return OperatingMode.ADVISORY
    return OperatingMode.FALLBACK


# Allowed transitions. MANUAL is always reachable by operator intent.
_ALLOWED: dict[OperatingMode, set[OperatingMode]] = {
    OperatingMode.AUTONOMOUS: {
        OperatingMode.GUARDED,
        OperatingMode.ADVISORY,
        OperatingMode.FALLBACK,
        OperatingMode.MANUAL,
    },
    OperatingMode.GUARDED: {
        OperatingMode.AUTONOMOUS,
        OperatingMode.ADVISORY,
        OperatingMode.FALLBACK,
        OperatingMode.MANUAL,
    },
    OperatingMode.ADVISORY: {
        OperatingMode.GUARDED,
        OperatingMode.AUTONOMOUS,
        OperatingMode.FALLBACK,
        OperatingMode.MANUAL,
    },
    OperatingMode.FALLBACK: {
        OperatingMode.ADVISORY,
        OperatingMode.GUARDED,
        OperatingMode.MANUAL,
    },
    OperatingMode.MANUAL: {
        OperatingMode.ADVISORY,
        OperatingMode.GUARDED,
        OperatingMode.FALLBACK,
        OperatingMode.AUTONOMOUS,
    },
}


def transition_mode(
    current: OperatingMode | str,
    proposed: OperatingMode | str,
    *,
    force: bool = False,
) -> OperatingMode:
    """Move between modes using a deterministic allow-list."""
    current_mode = OperatingMode(current)
    proposed_mode = OperatingMode(proposed)
    if current_mode == proposed_mode:
        return current_mode
    if force or proposed_mode in _ALLOWED[current_mode]:
        return proposed_mode
    raise ValueError(f"Illegal mode transition: {current_mode.value} -> {proposed_mode.value}")


def mode_allows_auto_apply(mode: OperatingMode | str, risk_level: str) -> bool:
    mode = OperatingMode(mode)
    risk = risk_level.upper()
    if mode == OperatingMode.AUTONOMOUS:
        return risk in {"LOW", "MEDIUM"}
    if mode == OperatingMode.GUARDED:
        return risk == "LOW"
    return False


def mode_requires_approval(mode: OperatingMode | str) -> bool:
    return OperatingMode(mode) in {OperatingMode.ADVISORY, OperatingMode.MANUAL}


def degrade_for_faults(
    current: OperatingMode | str,
    faults: Iterable[str],
) -> OperatingMode:
    """Force a safer mode when critical faults are present."""
    current_mode = OperatingMode(current)
    fault_list = list(faults)
    if not fault_list:
        return current_mode
    if any(f.startswith("critical") for f in fault_list):
        return transition_mode(current_mode, OperatingMode.FALLBACK, force=True)
    if current_mode == OperatingMode.AUTONOMOUS:
        return transition_mode(current_mode, OperatingMode.GUARDED, force=True)
    return current_mode
