"""EnergyPlus experiment safety helpers and strict-mode adapter tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from twinpilot_simulator.ep_experiment import (
    EnergyPlusUnavailableError,
    SafetyLimits,
    propose_agent_cooling_setpoint,
    resolve_paths_from_env,
    validate_setpoint_action,
)
from twinpilot_simulator.energyplus import EnergyPlusAdapter
from twinpilot_simulator.base import SimulationConfig


def test_ep_validate_fallback_on_llm_timeout():
    ok, reasons, disposition = validate_setpoint_action(
        proposed=24.5,
        current=23.9,
        heating_setpoint=22.2,
        limits=SafetyLimits(),
        confidence=0.9,
        sensors_healthy=True,
        data_age_seconds=0.0,
        manual_override=False,
        llm_timed_out=True,
        mcp_failed=False,
    )
    assert ok is False
    assert disposition == "fallback"
    assert "llm_timeout" in reasons


def test_ep_validate_fallback_on_mcp_failure():
    ok, reasons, disposition = validate_setpoint_action(
        proposed=24.5,
        current=23.9,
        heating_setpoint=22.2,
        limits=SafetyLimits(),
        confidence=0.9,
        sensors_healthy=True,
        data_age_seconds=0.0,
        manual_override=False,
        llm_timed_out=False,
        mcp_failed=True,
    )
    assert ok is False
    assert disposition == "fallback"


def test_ep_validate_reject_out_of_range():
    ok, reasons, disposition = validate_setpoint_action(
        proposed=30.0,
        current=23.9,
        heating_setpoint=22.2,
        limits=SafetyLimits(),
        confidence=0.9,
        sensors_healthy=True,
        data_age_seconds=0.0,
        manual_override=False,
        llm_timed_out=False,
        mcp_failed=False,
    )
    assert ok is False
    assert disposition == "rejected"
    assert "cooling_setpoint_out_of_range" in reasons


def test_agent_proposal_handles_missing_temps():
    sp, reason, conf = propose_agent_cooling_setpoint(
        outdoor_c=30.0,
        zone_temps={},
        occupancy={},
        current_cooling_setpoint=23.9,
        limits=SafetyLimits(),
    )
    assert sp == 23.9
    assert reason == "missing_zone_temperature"
    assert conf == 0.0


def test_agent_proposal_handles_impossible_temps():
    sp, reason, conf = propose_agent_cooling_setpoint(
        outdoor_c=30.0,
        zone_temps={"SPACE1-1": 120.0},
        occupancy={"SPACE1-1": 1.0},
        current_cooling_setpoint=23.9,
        limits=SafetyLimits(),
    )
    assert reason == "impossible_temperature"
    assert conf == 0.0


def test_strict_adapter_raises_when_unconfigured(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ENERGYPLUS_HOME", raising=False)
    monkeypatch.delenv("ENERGYPLUS_MODEL_PATH", raising=False)
    monkeypatch.delenv("ENERGYPLUS_WEATHER_PATH", raising=False)
    monkeypatch.delenv("ENERGYPLUS_ALLOW_MOCK_FALLBACK", raising=False)
    adapter = EnergyPlusAdapter()
    with pytest.raises(EnergyPlusUnavailableError):
        adapter.initialize(SimulationConfig())


def test_resolve_paths_fails_without_binary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ENERGYPLUS_HOME", str(tmp_path / "missing"))
    monkeypatch.setenv("ENERGYPLUS_MODEL_PATH", str(tmp_path / "a.idf"))
    monkeypatch.setenv("ENERGYPLUS_WEATHER_PATH", str(tmp_path / "a.epw"))
    (tmp_path / "a.idf").write_text("x")
    (tmp_path / "a.epw").write_text("x")
    with pytest.raises(EnergyPlusUnavailableError):
        resolve_paths_from_env(tmp_path / "out")


@pytest.mark.integration
def test_real_energyplus_baseline_if_installed():
    home = Path(os.getenv("ENERGYPLUS_HOME", "third_party/EnergyPlus"))
    if not (home / "energyplus").exists():
        pytest.skip("EnergyPlus not installed")
    from twinpilot_simulator.ep_experiment import ExperimentConfig, run_experiment, resolve_paths_from_env

    out = Path("results/baseline")
    paths = resolve_paths_from_env(out)
    summary = run_experiment(ExperimentConfig(paths=paths, mode="baseline"))
    assert summary["simulation_status"] == "completed"
    assert summary["total_energy_kwh"] > 0
    assert summary["mocked_components"] == []
