# Testing

## Unit / component (API workspace)

Located under `services/api/tests/`:

| File | Coverage |
|------|----------|
| `test_safety.py` | Safety Shield ranges, rate limits, mode gates |
| `test_objective_modes.py` | Objective weights / operating modes |

Run:

```bash
cd services/api
source ../../.venv/bin/activate
pytest -q
```

These tests import `twinpilot_optimizer` directly (no live server required).

---

## Integration

`tests/integration/test_control_flow.py` uses FastAPI `TestClient` against `app.main:app` (preferred) so CI does not need a separately running server. If `TWINPILOT_API_URL` points at a live API, the same flows can be exercised over HTTP.

Covers (happy path / smoke):

1. Login with demo manager
2. List buildings / status
3. Generate optimization plans
4. Validate (and optionally simulate) a plan
5. Health endpoint

```bash
cd tests/integration
PYTHONPATH=../../services/api:../../services/optimizer:../../services/simulator:../../services/agent \
  pytest -q
```

Or: `make test`

---

## Frontend

```bash
pnpm --filter @twinpilot/web typecheck
pnpm --filter @twinpilot/web lint
```

Mobile: `pnpm --filter @twinpilot/mobile typecheck` (optional; Expo lint available).

---

## CI

`.github/workflows/ci.yml` runs:

1. Python venv + editable installs
2. `pytest` in `services/api` (+ integration)
3. `pnpm install` + web typecheck/lint

---

## Manual demo verification

Follow [DEMO_SCRIPT.md](DEMO_SCRIPT.md). Confirm scenario endpoints under `/api/v1/demo/scenarios`.

---

## Gaps (honest)

- No end-to-end Playwright suite yet
- EnergyPlus path is smoke-checked via `make energyplus-check`, not full co-sim CI
- Mobile is typechecked optionally, not in default CI
