"""Candidate plan generation for the control loop."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from twinpilot_optimizer.objective import ObjectiveWeights, PlanMetrics, ScoreBreakdown, score_plan


class PlanSource(str, Enum):
    FIXED_BASELINE = "FIXED_BASELINE"
    RULE_BASED = "RULE_BASED"
    OCCUPANCY_SETBACK = "OCCUPANCY_SETBACK"
    CARBON_PRECOOL = "CARBON_PRECOOL"
    PEAK_SHAVING = "PEAK_SHAVING"
    BALANCED = "BALANCED"


class ZoneSetpointAction(BaseModel):
    zone_id: str
    action_type: str = "cooling_setpoint"
    current_value: float
    proposed_value: float
    duration_minutes: int = 60
    unit: str = "°C"


class CandidatePlan(BaseModel):
    plan_id: str
    plan_name: str
    source: PlanSource
    actions: list[ZoneSetpointAction]
    metrics: PlanMetrics
    score: ScoreBreakdown
    confidence: float
    simulation_status: str = "PENDING"
    hvac_schedule: str | None = None
    notes: list[str] = Field(default_factory=list)


class BuildingObservation(BaseModel):
    outdoor_temperature: float
    carbon_intensity: float
    electricity_tariff: float
    total_power_kw: float
    occupancy_total: int
    hour: int
    zones: dict[str, dict[str, Any]]
    peak_window: bool = False
    carbon_rising: bool = False
    occupancy_spike_zone: str | None = None


def generate_candidate_plans(
    observation: BuildingObservation,
    weights: ObjectiveWeights,
    *,
    energy_target_pct: float | None = None,
    allow_schedule_changes: bool = True,
    zero_comfort_deviation: bool = False,
) -> list[CandidatePlan]:
    """Generate baseline, rule-based and optimization candidates."""
    zones = observation.zones
    plans: list[CandidatePlan] = []

    # Fixed baseline — no changes
    baseline_actions = [
        ZoneSetpointAction(
            zone_id=zid,
            current_value=float(z["cooling_setpoint"]),
            proposed_value=float(z["cooling_setpoint"]),
        )
        for zid, z in zones.items()
    ]
    baseline_metrics = PlanMetrics(
        energy_saving_pct=0.0,
        cost_saving_pct=0.0,
        carbon_saving_pct=0.0,
        peak_reduction_pct=0.0,
        comfort_violation_minutes=0.0,
        equipment_moves=0.0,
        risk_score=0.05,
        feasible=True,
    )
    plans.append(
        CandidatePlan(
            plan_id="plan_baseline",
            plan_name="Fixed schedule baseline",
            source=PlanSource.FIXED_BASELINE,
            actions=baseline_actions,
            metrics=baseline_metrics,
            score=score_plan(baseline_metrics, weights),
            confidence=0.95,
            hvac_schedule="08:00-19:00",
            notes=["HVAC operates on fixed occupied schedule", "No setpoint changes"],
        )
    )

    # Rule-based
    rule_actions = []
    for zid, z in zones.items():
        current = float(z["cooling_setpoint"])
        occ = int(z.get("occupancy_count", 0))
        proposed = current
        if occ == 0 and allow_schedule_changes:
            proposed = min(current + 1.0, 27.0)
        elif observation.outdoor_temperature >= 32:
            proposed = min(current + 0.3, 26.0)
        rule_actions.append(
            ZoneSetpointAction(zone_id=zid, current_value=current, proposed_value=round(proposed, 1))
        )
    rule_save = 6.5 if observation.outdoor_temperature >= 30 else 3.5
    if observation.occupancy_spike_zone:
        rule_save *= 0.6
    rule_metrics = PlanMetrics(
        energy_saving_pct=rule_save,
        cost_saving_pct=rule_save * 0.9,
        carbon_saving_pct=rule_save * 0.85,
        peak_reduction_pct=4.0,
        comfort_violation_minutes=2.0 if observation.occupancy_spike_zone else 0.0,
        equipment_moves=float(sum(1 for a in rule_actions if a.proposed_value != a.current_value)),
        risk_score=0.15,
        feasible=True,
    )
    plans.append(
        CandidatePlan(
            plan_id="plan_rule",
            plan_name="Rule-based controller",
            source=PlanSource.RULE_BASED,
            actions=rule_actions,
            metrics=rule_metrics,
            score=score_plan(rule_metrics, weights),
            confidence=0.88,
            notes=["Occupancy and outdoor-temperature heuristics"],
        )
    )

    # Occupancy setback
    setback_actions = []
    for zid, z in zones.items():
        current = float(z["cooling_setpoint"])
        occ_prob = float(z.get("occupancy_probability", 0.5))
        bump = 1.2 if occ_prob < 0.35 else (0.5 if occ_prob < 0.7 else 0.0)
        if observation.occupancy_spike_zone == zid:
            bump = -0.3
        setback_actions.append(
            ZoneSetpointAction(
                zone_id=zid,
                current_value=current,
                proposed_value=round(min(max(current + bump, 21.0), 27.0), 1),
            )
        )
    setback_metrics = PlanMetrics(
        energy_saving_pct=11.0,
        cost_saving_pct=10.0,
        carbon_saving_pct=9.5,
        peak_reduction_pct=5.5,
        comfort_violation_minutes=8.0 if observation.occupancy_spike_zone else 1.0,
        equipment_moves=3.0,
        risk_score=0.25,
        feasible=not zero_comfort_deviation or not observation.occupancy_spike_zone,
        infeasibility_reasons=(
            ["Zero comfort deviation conflicts with aggressive setback during occupancy spike"]
            if zero_comfort_deviation and observation.occupancy_spike_zone
            else []
        ),
    )
    plans.append(
        CandidatePlan(
            plan_id="plan_setback",
            plan_name="Occupancy setback plan",
            source=PlanSource.OCCUPANCY_SETBACK,
            actions=setback_actions,
            metrics=setback_metrics,
            score=score_plan(setback_metrics, weights),
            confidence=0.84,
            notes=["Raises setpoints where occupancy probability is low"],
        )
    )

    # Carbon-aware pre-cooling
    precool_actions = []
    for zid, z in zones.items():
        current = float(z["cooling_setpoint"])
        if observation.carbon_rising and observation.hour < 16:
            proposed = max(current - 0.7, 21.5)
        else:
            proposed = min(current + 0.4, 26.5)
        precool_actions.append(
            ZoneSetpointAction(zone_id=zid, current_value=current, proposed_value=round(proposed, 1))
        )
    carbon_save = 14.8 if observation.carbon_rising else 7.0
    precool_metrics = PlanMetrics(
        energy_saving_pct=8.5 if observation.carbon_rising else 5.0,
        cost_saving_pct=7.2,
        carbon_saving_pct=carbon_save,
        peak_reduction_pct=3.0,
        comfort_violation_minutes=0.0,
        equipment_moves=4.0,
        risk_score=0.2,
        feasible=True,
    )
    plans.append(
        CandidatePlan(
            plan_id="plan_carbon",
            plan_name="Carbon-aware pre-cooling plan",
            source=PlanSource.CARBON_PRECOOL,
            actions=precool_actions,
            metrics=precool_metrics,
            score=score_plan(precool_metrics, weights),
            confidence=0.86,
            notes=[
                "Pre-cools while carbon intensity is lower",
                "Shifts load away from carbon-intensive periods",
            ],
        )
    )

    # Peak shaving
    peak_actions = []
    for zid, z in zones.items():
        current = float(z["cooling_setpoint"])
        proposed = min(current + (1.0 if observation.peak_window else 0.4), 27.0)
        if observation.occupancy_spike_zone == zid:
            proposed = current
        peak_actions.append(
            ZoneSetpointAction(zone_id=zid, current_value=current, proposed_value=round(proposed, 1))
        )
    peak_metrics = PlanMetrics(
        energy_saving_pct=9.0,
        cost_saving_pct=12.5,
        carbon_saving_pct=8.0,
        peak_reduction_pct=12.0 if observation.peak_window else 6.0,
        comfort_violation_minutes=4.0,
        equipment_moves=3.0,
        risk_score=0.3,
        feasible=True,
    )
    plans.append(
        CandidatePlan(
            plan_id="plan_peak",
            plan_name="Peak-shaving plan",
            source=PlanSource.PEAK_SHAVING,
            actions=peak_actions,
            metrics=peak_metrics,
            score=score_plan(peak_metrics, weights),
            confidence=0.82,
            notes=["Reduces coincident HVAC demand during tariff peaks"],
        )
    )

    # Balanced optimization
    balanced_actions = []
    for zid, z in zones.items():
        current = float(z["cooling_setpoint"])
        proposed = current + 0.5
        if observation.occupancy_spike_zone == zid:
            proposed = current - 0.2
        if observation.carbon_rising and observation.hour < 15:
            proposed = current - 0.3
        balanced_actions.append(
            ZoneSetpointAction(
                zone_id=zid,
                current_value=current,
                proposed_value=round(min(max(proposed, 21.5), 26.5), 1),
                duration_minutes=60,
            )
        )
    balanced_energy = 11.2
    if energy_target_pct is not None and energy_target_pct > 25 and zero_comfort_deviation:
        # Explicitly infeasible aggressive target
        infeas = PlanMetrics(
            energy_saving_pct=0.0,
            feasible=False,
            infeasibility_reasons=[
                "The requested target is not feasible under current weather, occupancy and comfort constraints. "
                "The maximum predicted safe saving is 17.8%."
            ],
        )
        plans.append(
            CandidatePlan(
                plan_id="plan_requested",
                plan_name="Requested aggressive target",
                source=PlanSource.BALANCED,
                actions=balanced_actions,
                metrics=infeas,
                score=score_plan(infeas, weights),
                confidence=0.4,
                notes=["Operator request marked infeasible"],
            )
        )
        balanced_energy = 17.8

    balanced_metrics = PlanMetrics(
        energy_saving_pct=balanced_energy,
        cost_saving_pct=9.4,
        carbon_saving_pct=12.0 if observation.carbon_rising else 10.5,
        peak_reduction_pct=7.0,
        comfort_violation_minutes=0.0,
        equipment_moves=2.0,
        risk_score=0.12,
        feasible=True,
    )
    plans.append(
        CandidatePlan(
            plan_id="plan_balanced",
            plan_name="Balanced optimization plan",
            source=PlanSource.BALANCED,
            actions=balanced_actions,
            metrics=balanced_metrics,
            score=score_plan(balanced_metrics, weights),
            confidence=0.91,
            notes=[
                "Maintains occupied comfort",
                "Balances energy, cost, carbon and peak objectives",
            ],
        )
    )

    return plans


def select_best_plan(plans: list[CandidatePlan]) -> CandidatePlan | None:
    feasible = [p for p in plans if p.metrics.feasible and p.source != PlanSource.FIXED_BASELINE]
    if not feasible:
        feasible = [p for p in plans if p.metrics.feasible]
    if not feasible:
        return None
    return max(feasible, key=lambda p: p.score.utility)
