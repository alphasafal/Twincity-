# Final Claims — Eco-Loop Building Agents

## Primary claim (Path A — authoritative)

Under identical EnergyPlus building, weather, occupancy and simulation conditions, Eco-Loop reduced simulated HVAC energy by **4.98%**, total energy by **1.31%** and peak demand by **1.47%**, while maintaining **zero** occupied comfort-violation hours and **zero** comfort degree-hours.

| Metric | Baseline | Eco-Loop | Improvement |
|--------|----------|----------|-------------|
| Total energy | 421.51 kWh | 416.00 kWh | 1.31% |
| HVAC energy | 13.85 kWh | 13.16 kWh | 4.98% |
| Peak power | 19.93 kW | 19.64 kW | 1.47% |
| Comfort violations | 0 h | 0 h | — |
| Comfort degree-hours | 0 | 0 | — |
| Actions | — | 48 approved / 0 rejected / 0 fallback | — |

Evidence: `evidence/independent-metrics.json`, `evidence/energyplus/comparison.json`, `evidence/experiment-fairness.md`

## Multi-scenario Path A (fair comparisons)

| Scenario | Total saving | HVAC saving | Peak reduction | Comfort |
|----------|--------------|-------------|----------------|---------|
| Normal summer | 1.31% | 4.98% | 1.47% | 0 h |
| Hot / peak day | 1.27% | 5.07% | 1.08% | 0 h |
| High occupancy | 1.34% | 5.18% | 1.45% | 0 h |

Evidence: `results/scenarios/consolidated_comparison.json`

## Path C — hybrid supervisory (LLM materially in the loop)

Ollama selects energy-conservation strategies via MCP tools; the deterministic optimiser computes setpoints; SafetyShield gates actuation; expected-vs-actual outcomes are logged for self-correction.

Representative hybrid run (**not** a replacement for Path A claims):
- Separate MCP client/server PIDs (`mcp_pids_differ: true`)
- Strategies selected: COMFORT_FIRST, ECO_MODE, UNOCCUPIED_SETBACK, PRE_COOL, HOLD_CURRENT_POLICY
- Actions: **48 approved / 0 rejected / 0 fallback**
- HVAC ≈ **3.68%** / total ≈ **0.99%** vs same baseline (Path A remains the authoritative **4.98% / 1.31% / 1.47%** claim)
- Comfort violations: **0 h**
- Note: Path C peak can vary with strategy mix; do not substitute Path C peak for Path A
- Self-correction: `evidence/hybrid/self_correction.jsonl`
- Loop excerpt: `evidence/hybrid/five-step-loop-excerpt.jsonl`
- Script: `./scripts/run_hybrid_supervisory_experiment.sh`

## Supporting claims

| Claim | Evidence |
|---|---|
| MCP separate stdio process | `evidence/mcp-process-proof.md`, `evidence/mcp-runtime-trace.jsonl` |
| Ollama structured proposals | `evidence/ollama-runtime-proof.md` |
| SafetyShield rejects 35°C | `evidence/safety-rejection.log` |
| Actuator write to Clg-SetP-Sch | `evidence/final-actuator-trace.csv` |
| Next EnergyPlus state returned | `evidence/final-next-state-proof.md` |
| Ollama failure → deterministic fallback | `evidence/ollama-fallback.log` |
| Dashboard real data integrity | `evidence/dashboard-real-data-proof.md` |
| Dashboard honest no-data | `evidence/dashboard-no-data-proof.md` |
| Clean-clone | `evidence/clean-clone-report.md` |
| Carbon is estimated | comparison `carbon_accounting` (0.417 kg/kWh) |
| Hybrid supervisory Path C | `results/hybrid/summary.json`, `JUDGE_QA.md` |

## Non-claims
- Not a physical BMS deployment.
- Not universal savings across buildings/weather.
- Not presenting 12.20% HVAC as comfort-zero authoritative.
- Not claiming Path A 4.98% was produced solely by the LLM writing every setpoint.
- Not calling in-process handler dispatch “MCP transport”.
