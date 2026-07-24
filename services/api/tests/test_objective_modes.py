"""Objective scoring and mode state machine tests."""

from __future__ import annotations

import pytest

from twinpilot_optimizer.confidence import ConfidenceInputs, compute_confidence
from twinpilot_optimizer.modes import OperatingMode, recommend_mode, transition_mode
from twinpilot_optimizer.objective import ObjectiveWeights, PlanMetrics, score_plan
from twinpilot_optimizer.anomaly import SensorSeries, detect_temperature_anomalies
from twinpilot_agent.providers import DeterministicAgentProvider, AgentPlanOutput


def test_weights_normalize():
    w = ObjectiveWeights(
        energy_weight=2,
        cost_weight=2,
        carbon_weight=2,
        comfort_weight=2,
        peak_weight=1,
        equipment_weight=1,
    )
    total = (
        w.energy_weight
        + w.cost_weight
        + w.carbon_weight
        + w.comfort_weight
        + w.peak_weight
        + w.equipment_weight
    )
    assert abs(total - 1.0) < 1e-9


def test_infeasible_plan_cannot_win():
    weights = ObjectiveWeights()
    bad = score_plan(
        PlanMetrics(energy_saving_pct=90, feasible=False, infeasibility_reasons=["nope"]),
        weights,
    )
    good = score_plan(PlanMetrics(energy_saving_pct=10, feasible=True), weights)
    assert bad.utility < 0
    assert good.utility > bad.utility


def test_mode_recommendations():
    assert recommend_mode(0.9) == OperatingMode.AUTONOMOUS
    assert recommend_mode(0.7) == OperatingMode.GUARDED
    assert recommend_mode(0.5) == OperatingMode.ADVISORY
    assert recommend_mode(0.2) == OperatingMode.FALLBACK
    assert recommend_mode(0.99, critical_fault=True) == OperatingMode.FALLBACK


def test_illegal_transition_raises():
    with pytest.raises(ValueError):
        # FALLBACK -> AUTONOMOUS is not directly allowed without force
        transition_mode(OperatingMode.FALLBACK, OperatingMode.AUTONOMOUS, force=False)


def test_confidence_clamp_and_breakdown():
    breakdown = compute_confidence(
        ConfidenceInputs(
            sensor_health=1,
            data_freshness=1,
            forecast_confidence=1,
            simulation_confidence=1,
            model_accuracy=1,
            service_health=1,
        )
    )
    assert breakdown.score == 1.0
    assert "sensor_health" in breakdown.weights


def test_implausible_sensor_rule():
    findings = detect_temperature_anomalies(
        SensorSeries(zone_id="north", values=[55.0], timestamps_age_seconds=[5])
    )
    assert any(f.rule == "implausible_temperature" for f in findings)


@pytest.mark.asyncio
async def test_structured_llm_fallback_output():
    agent = DeterministicAgentProvider()
    out = await agent.explain({"question": "Why is the system in Guarded Mode?", "mode": "GUARDED"})
    assert isinstance(out, AgentPlanOutput)
    assert out.observation
    assert out.executed_action is not None
