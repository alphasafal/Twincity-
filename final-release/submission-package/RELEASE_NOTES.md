# Release Notes — Eco-Loop Building Agents

**Commit:** `f0f94d84d08969784cf2373ddbb3cca6e3fa909b`
**Branch:** `cursor/ecolooop-energyplus-audit-b6b3`
**Generated:** 2026-07-25T12:01:39.455435+00:00

## Included
- Verified EnergyPlus Runtime API closed loop (Path A comfort-zero).
- Separate MCP client/server over stdio for LLM path.
- Local Ollama structured proposals gated by SafetyShield.
- Honest dashboard `DATA_MODE=energyplus` no-data state.
- Final-release evidence pack.

## Authoritative Path A results (fresh)
- Total: 421.51 → 416.00 kWh (1.31%)
- HVAC: 13.85 → 13.16 kWh (4.98%)
- Peak: 19.93 → 19.64 kW (1.47%)
- Comfort: 0 h / 0 degree-hours
- Actions: 48 approved / 0 rejected / 0 fallback

## Not authoritative
- Prior 12.20% HVAC figure is **not** the comfort-zero result.
- LLM-path energy totals are secondary and model-variable.

## Engineering fixes in this pass
- `tests/integration/test_control_flow.py` accepts energyplus real-data semantics.
- Added `final_acceptance.sh`, `final_smoke_test.sh`, `final_submission_check.sh`.
