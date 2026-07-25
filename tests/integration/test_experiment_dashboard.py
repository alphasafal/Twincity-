"""DATA_MODE=energyplus dashboard payload integrity.

These checks validate the measured EnergyPlus experiment artifacts under
``results/*``. Those artifacts are generated locally (``scripts/run_baseline.sh``
+ ``scripts/run_agent.sh``) and are intentionally not committed, so when they are
absent (e.g. a fresh CI checkout without EnergyPlus) the checks skip instead of
failing.
"""

from __future__ import annotations

import pytest

from app.services.experiment_store import experiment_dashboard_payload


def _require_experiment_payload():
    payload = experiment_dashboard_payload("default")
    if not payload.get("available"):
        pytest.skip(
            "EnergyPlus experiment results not present; run scripts/run_baseline.sh "
            "and scripts/run_agent.sh to generate results/*."
        )
    return payload


def test_experiment_payload_has_real_reductions_no_synthetic():
    payload = _require_experiment_payload()
    assert payload["available"] is True
    assert payload["synthetic_multiplier_applied"] is False
    assert payload["simulated"] is False
    assert payload["baseline"]["total_energy_kwh"] > 0
    assert payload["agent"]["total_energy_kwh"] > 0
    # Percentages derived from source summary values (full precision), not invented.
    assert payload["reductions"]["total_energy_pct"] is not None
    assert payload["reductions"]["total_energy_pct"] > 0
    assert payload["reductions"]["formula"] == "(baseline - agent) / baseline * 100"
    assert payload["action_counts"]["approved"] >= 0
    assert "estimate" in payload["carbon_accounting"]["label"]


def test_comfort_zero_after_hardening():
    payload = _require_experiment_payload()
    assert payload["agent"]["occupied_comfort_violation_hours"] == 0.0
    assert payload["baseline"]["occupied_comfort_violation_hours"] == 0.0
