# Final Claims — Eco-Loop Building Agents

**Final release commit:** `f0f94d84d08969784cf2373ddbb3cca6e3fa909b`
**Generated:** 2026-07-25T12:01:39.455435+00:00

> Internal engineering-readiness score is recorded in `FINAL_RELEASE_MANIFEST.json`.
> It is **not** a judge score or predicted competition score.

## Primary claim

Under identical EnergyPlus building, weather, occupancy and simulation conditions, Eco-Loop reduced simulated HVAC energy by **4.98%**, total energy by **1.31%** and peak demand by **1.47%**, while maintaining **zero** occupied comfort-violation hours and **zero** comfort degree-hours.

Evidence: `evidence/independent-metrics.json`, `evidence/energyplus/comparison.json`, `evidence/independent-comfort-summary.json`, `evidence/experiment-fairness.md`

## Supporting claims

| Claim | Evidence |
|---|---|
| MCP separate stdio process | `evidence/mcp-process-proof.md`, `evidence/mcp-runtime-trace.jsonl` (PIDs 65999 ≠ 66004) |
| Ollama structured proposals | `evidence/ollama-runtime-proof.md`, `evidence/ollama-structured-responses.jsonl` |
| SafetyShield rejects 35°C | `evidence/safety-rejection.log` |
| Actuator write to Clg-SetP-Sch | `evidence/final-actuator-trace.csv` |
| Next EnergyPlus state returned | `evidence/final-next-state-proof.md` |
| Ollama failure → deterministic fallback | `evidence/ollama-fallback.log` |
| Recovery after failure | `evidence/recovery-after-failure.md` |
| Dashboard real data integrity | `evidence/dashboard-real-data-proof.md` |
| Dashboard honest no-data | `evidence/dashboard-no-data-proof.md` |
| Clean-clone | `evidence/clean-clone-report.md`, `logs/clean-clone.log` |
| Carbon is estimated | comparison `carbon_accounting` (0.417 kg/kWh) |

## Non-claims
- Not a physical BMS deployment.
- Not universal savings across buildings/weather.
- Not presenting 12.20% HVAC as comfort-zero authoritative.
- Not calling in-process handler dispatch “MCP transport”.
