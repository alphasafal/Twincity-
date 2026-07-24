"""Platform tenancy, entitlements, and HMAC token smoke tests."""

from __future__ import annotations

from twinpilot_optimizer.safety import build_validation_token, verify_validation_token

from app.services.entitlements import entitlements_for_plan


def test_plan_entitlements_autonomy_allows_write():
    starter = entitlements_for_plan("starter")
    autonomy = entitlements_for_plan("autonomy")
    assert starter["autonomous_write"] is False
    assert autonomy["autonomous_write"] is True
    assert "honeywell_niagara" in autonomy["connector_types"]


def test_hmac_validation_token_roundtrip():
    secret = "unit-test-validation-secret"
    token = build_validation_token("plan-1", "hash-abc", "tester", secret=secret, ttl_seconds=60)
    assert token.startswith("v2:")
    parsed = verify_validation_token(token, plan_id="plan-1", state_hash="hash-abc", secret=secret)
    assert parsed["signed"] is True
    assert parsed["nonce"]


def test_hmac_token_rejects_tamper():
    secret = "unit-test-validation-secret"
    token = build_validation_token("plan-1", "hash-abc", "tester", secret=secret)
    bad = token[:-4] + "dead"
    try:
        verify_validation_token(bad, plan_id="plan-1", secret=secret)
        assert False, "expected ValueError"
    except ValueError:
        pass
