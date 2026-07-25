# Test Summary

Generated: 2026-07-25T11:54:39.954556+00:00
HEAD (at test time): see repository; final release commit sealed after docs commit.

## Classification

| Check | Result | Severity if fail |
|---|---|---|
| pytest simulator+optimizer+api+integration | see below | P0/P1 |
| MCP/safety related subset | PASS (earlier) | P0 |
| Shell syntax | PASS | P1 |
| Frontend lint | PASS | P1 |
| Frontend typecheck | PASS | P1 |
| Frontend production build | PASS | P0 |
| Docker build | Not part of documented demo workflow — skipped | — |

## Corrected pytest command (README-aligned)

```
PYTHONPATH=services/api:services/optimizer:services/simulator:services/agent:services/mcp-server \
  .venv/bin/python -m pytest services/simulator/tests services/optimizer/tests services/api/tests tests/integration -q --tb=line
```

### Output (tail)

```
.........................................................                [100%]
=============================== warnings summary ===============================
services/simulator/tests/test_ep_experiment_safety.py:119
  /workspace/services/simulator/tests/test_ep_experiment_safety.py:119: PytestUnknownMarkWarning: Unknown pytest.mark.integration - is this a typo?  You can register custom marks to avoid this warning - for details, see https://docs.pytest.org/en/stable/how-to/mark.html
    @pytest.mark.integration

.venv/lib/python3.12/site-packages/fastapi/testclient.py:1
  /workspace/.venv/lib/python3.12/site-packages/fastapi/testclient.py:1: StarletteDeprecationWarning: Using `httpx` with `starlette.testclient` is deprecated; install `httpx2` instead.
    from starlette.testclient import TestClient as TestClient  # noqa

.venv/lib/python3.12/site-packages/passlib/utils/__init__.py:854
  /workspace/.venv/lib/python3.12/site-packages/passlib/utils/__init__.py:854: DeprecationWarning: 'crypt' is deprecated and slated for removal in Python 3.13
    from crypt import crypt as _crypt

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
57 passed, 3 warnings in 5.21s

```

## P0 / P1 fixes applied during final release

- **P1:** `tests/integration/test_control_flow.py` asserted `simulated is True`, which is incorrect when `DATA_MODE=energyplus` and results exist. Updated to accept energyplus real-data / unavailable labels.

## Notes

- Do not run bare `pytest` from repo root without ignoring `third_party/EnergyPlus` — EnergyPlus bundles idlelib tests that abort collection.
- `tests/unit` path does not exist; use service test dirs + `tests/integration`.
