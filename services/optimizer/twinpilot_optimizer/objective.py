"""Normalized multi-objective scoring for candidate control plans."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class ObjectiveWeights(BaseModel):
    energy_weight: float = 0.25
    cost_weight: float = 0.20
    carbon_weight: float = 0.20
    comfort_weight: float = 0.20
    peak_weight: float = 0.10
    equipment_weight: float = 0.05

    @model_validator(mode="after")
    def normalize(self) -> ObjectiveWeights:
        total = (
            self.energy_weight
            + self.cost_weight
            + self.carbon_weight
            + self.comfort_weight
            + self.peak_weight
            + self.equipment_weight
        )
        if total <= 0:
            raise ValueError("Objective weights must sum to a positive value")
        self.energy_weight /= total
        self.cost_weight /= total
        self.carbon_weight /= total
        self.comfort_weight /= total
        self.peak_weight /= total
        self.equipment_weight /= total
        return self


class PlanMetrics(BaseModel):
    energy_saving_pct: float = 0.0
    cost_saving_pct: float = 0.0
    carbon_saving_pct: float = 0.0
    peak_reduction_pct: float = 0.0
    comfort_violation_minutes: float = 0.0
    equipment_moves: float = 0.0
    risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    feasible: bool = True
    infeasibility_reasons: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    utility: float
    feasible: bool
    energy_term: float
    cost_term: float
    carbon_term: float
    peak_term: float
    comfort_penalty: float
    equipment_penalty: float
    risk_penalty: float
    explanation: list[str]


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def normalize_saving(pct: float, cap: float = 40.0) -> float:
    """Map percentage savings into [0, 1], allowing mild negative values."""
    return _clamp01((pct + 5.0) / (cap + 5.0))


def normalize_comfort_penalty(minutes: float, cap: float = 60.0) -> float:
    return _clamp01(minutes / cap)


def normalize_equipment_penalty(moves: float, cap: float = 10.0) -> float:
    return _clamp01(moves / cap)


def score_plan(metrics: PlanMetrics, weights: ObjectiveWeights) -> ScoreBreakdown:
    """Hard feasibility first; only feasible plans receive a competitive utility."""
    if not metrics.feasible:
        return ScoreBreakdown(
            utility=-1.0,
            feasible=False,
            energy_term=0.0,
            cost_term=0.0,
            carbon_term=0.0,
            peak_term=0.0,
            comfort_penalty=0.0,
            equipment_penalty=0.0,
            risk_penalty=0.0,
            explanation=metrics.infeasibility_reasons
            or ["Plan marked infeasible before objective scoring"],
        )

    energy_term = weights.energy_weight * normalize_saving(metrics.energy_saving_pct)
    cost_term = weights.cost_weight * normalize_saving(metrics.cost_saving_pct)
    carbon_term = weights.carbon_weight * normalize_saving(metrics.carbon_saving_pct)
    peak_term = weights.peak_weight * normalize_saving(metrics.peak_reduction_pct)
    comfort_penalty = weights.comfort_weight * normalize_comfort_penalty(
        metrics.comfort_violation_minutes
    )
    equipment_penalty = weights.equipment_weight * normalize_equipment_penalty(
        metrics.equipment_moves
    )
    risk_penalty = 0.15 * metrics.risk_score

    utility = (
        energy_term
        + cost_term
        + carbon_term
        + peak_term
        - comfort_penalty
        - equipment_penalty
        - risk_penalty
    )

    explanation = [
        f"Energy term {energy_term:.3f} from {metrics.energy_saving_pct:.1f}% saving",
        f"Cost term {cost_term:.3f} from {metrics.cost_saving_pct:.1f}% saving",
        f"Carbon term {carbon_term:.3f} from {metrics.carbon_saving_pct:.1f}% saving",
        f"Peak term {peak_term:.3f} from {metrics.peak_reduction_pct:.1f}% reduction",
        f"Comfort penalty {comfort_penalty:.3f} from {metrics.comfort_violation_minutes:.0f} min",
        f"Equipment penalty {equipment_penalty:.3f} from {metrics.equipment_moves:.0f} moves",
        f"Risk penalty {risk_penalty:.3f}",
    ]
    return ScoreBreakdown(
        utility=round(utility, 4),
        feasible=True,
        energy_term=round(energy_term, 4),
        cost_term=round(cost_term, 4),
        carbon_term=round(carbon_term, 4),
        peak_term=round(peak_term, 4),
        comfort_penalty=round(comfort_penalty, 4),
        equipment_penalty=round(equipment_penalty, 4),
        risk_penalty=round(risk_penalty, 4),
        explanation=explanation,
    )
