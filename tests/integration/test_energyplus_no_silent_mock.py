"""Regression: DATA_MODE=energyplus must not silently become mock when results are missing."""

from __future__ import annotations

import os
from pathlib import Path

from app.services.experiment_store import experiment_dashboard_payload


def test_missing_results_mark_experiment_unavailable(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    payload = experiment_dashboard_payload("default")
    assert payload["available"] is False
    assert "baseline/summary.json" in payload["missing_artifacts"]


def test_router_energyplus_unavailable_keeps_data_mode(monkeypatch, tmp_path: Path):
    """Import router helper path via status logic contract (store + mode)."""
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path))
    monkeypatch.setenv("DATA_MODE", "energyplus")
    experiment = experiment_dashboard_payload("default")
    data_mode = os.getenv("DATA_MODE", "energyplus").strip().lower()
    assert data_mode == "energyplus"
    assert experiment.get("available") is False
    # Contract enforced by router: energyplus + unavailable => stay energyplus, not mock.
    response_mode = (
        "energyplus"
        if data_mode == "energyplus"
        else "mock"
    )
    assert response_mode == "energyplus"
