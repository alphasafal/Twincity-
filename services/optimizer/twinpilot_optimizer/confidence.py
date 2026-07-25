"""Autonomy confidence scoring with transparent breakdown."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConfidenceInputs(BaseModel):
    sensor_health: float = Field(ge=0.0, le=1.0)
    data_freshness: float = Field(ge=0.0, le=1.0)
    forecast_confidence: float = Field(ge=0.0, le=1.0)
    simulation_confidence: float = Field(ge=0.0, le=1.0)
    model_accuracy: float = Field(ge=0.0, le=1.0)
    service_health: float = Field(ge=0.0, le=1.0)


class ConfidenceBreakdown(BaseModel):
    score: float
    sensor_health: float
    data_freshness: float
    forecast_confidence: float
    simulation_confidence: float
    model_accuracy: float
    service_health: float
    weights: dict[str, float]


DEFAULT_WEIGHTS = {
    "sensor_health": 0.25,
    "data_freshness": 0.15,
    "forecast_confidence": 0.20,
    "simulation_confidence": 0.20,
    "model_accuracy": 0.10,
    "service_health": 0.10,
}


def compute_confidence(
    inputs: ConfidenceInputs,
    weights: dict[str, float] | None = None,
) -> ConfidenceBreakdown:
    w = weights or DEFAULT_WEIGHTS
    total_w = sum(w.values()) or 1.0
    normalized = {k: v / total_w for k, v in w.items()}

    score = (
        normalized["sensor_health"] * inputs.sensor_health
        + normalized["data_freshness"] * inputs.data_freshness
        + normalized["forecast_confidence"] * inputs.forecast_confidence
        + normalized["simulation_confidence"] * inputs.simulation_confidence
        + normalized["model_accuracy"] * inputs.model_accuracy
        + normalized["service_health"] * inputs.service_health
    )
    score = max(0.0, min(1.0, score))
    return ConfidenceBreakdown(
        score=round(score, 4),
        sensor_health=inputs.sensor_health,
        data_freshness=inputs.data_freshness,
        forecast_confidence=inputs.forecast_confidence,
        simulation_confidence=inputs.simulation_confidence,
        model_accuracy=inputs.model_accuracy,
        service_health=inputs.service_health,
        weights=normalized,
    )
