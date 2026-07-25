# Final 3-Minute Demo Script

**Commit:** `f0f94d84d08969784cf2373ddbb3cca6e3fa909b`

**Always say:** “AI proposes. SafetyShield validates. EnergyPlus executes.”
**Never say:** physical BMS deployment, or 12.20% HVAC as the comfort-zero result.

## 0:00–0:25 — Problem
**Words:** “Buildings waste energy when HVAC ignores occupancy and weather. Letting an LLM write setpoints directly is unsafe.”
**Show:** problem slide / README opener.

## 0:25–0:50 — Architecture
**Words:** “EnergyPlus is our digital building. Observations move through a real MCP client to a separate stdio server, then to local Ollama. SafetyShield is the only gate before the actuator.”
**Show:** architecture diagram.

## 0:50–1:35 — Real closed loop
**Commands (prefer pre-run):**
```bash
./scripts/run_baseline.sh && ./scripts/run_agent.sh && ./scripts/compare_results.sh
```
**Words:** “These rows show Clg-SetP-Sch written and the next zone temperature returned.”
**Show:** `final-release/evidence/final-actuator-trace.csv`
**Fallback:** “Live EnergyPlus is pre-verified at commit f0f94d84d089; here are five consecutive actuator→next-state rows.”

## 1:35–2:05 — Results
**Words:** “Identical inputs: HVAC about 4.98% lower, total energy 1.31% lower, peak 1.47% lower, zero comfort violations.”
**Show:** dashboard or `results/comparison/comparison.md`.

## 2:05–2:35 — Safety and fallback
**Words:** “Thirty-five degrees is rejected. If Ollama is down, deterministic fallback continues — still through SafetyShield.”
**Show:** `safety-rejection.log`, `ollama-fallback.log`.

## 2:35–3:00 — Closing
**Words:** “Reproducible EnergyPlus prototype, not a physical BMS. AI proposes. SafetyShield validates. EnergyPlus executes.”
**Show:** primary claim in `FINAL_CLAIMS.md`.
