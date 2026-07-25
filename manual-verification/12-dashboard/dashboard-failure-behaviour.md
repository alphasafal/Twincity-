# Dashboard Failure Behaviour (Phase 12)

| Test | Result |
|------|--------|
| Backend stopped | connection failure (HTTP 000) |
| Missing results + DATA_MODE=energyplus | falls through to mock-labeled block (**P0**) |
| Corrupt comparison | comparison null |
| DATA_MODE=mock | mock mode, savings 0.0 |
| ×1.12 | not applied |

Evidence under `dashboard-api-responses/`.
