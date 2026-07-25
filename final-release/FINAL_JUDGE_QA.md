# Final Judge Q&A

**Commit:** `39cb4da36b9f79de36aa797de28de5bb0a76f950` · **Generated:** 2026-07-25T12:01:39.455435+00:00

## 1. Why use an LLM instead of only rules?
**A:** Rules cover known heuristics; the LLM proposes context-aware setpoints. SafetyShield still decides. Path A is the authoritative savings proof.

## 2. Why is total energy reduction lower than HVAC reduction?
**A:** HVAC is a small share of facility energy; lights/equipment dominate, so HVAC % moves more than whole-building %.

## 3. How do you prove EnergyPlus is really controlled?
**A:** Runtime API set_actuator_value on Clg-SetP-Sch, energyplus_actuator_written=true, and next-timestep temperatures change.

## 4. What exactly does MCP do?
**A:** A separate local tool server over stdio exposing observation/context tools to the experiment client.

## 5. How do you prove MCP is not simulated?
**A:** Client PID 65999 ≠ server PID 66004; initialize/tools/list/tools/call are in the JSONL trace.

## 6. Can the LLM directly control the actuator?
**A:** No. LLM output is a proposal only; SafetyShield must approve before any actuator write.

## 7. What happens when Ollama fails?
**A:** Failure is logged; deterministic fallback proposes; SafetyShield still gates; we observed 48 fallback actions.

## 8. What happens when MCP fails?
**A:** Tool calls fail closed into deterministic_fallback; no unsafe bypass.

## 9. What happens when EnergyPlus fails?
**A:** Scripts exit non-zero with failed status; dashboard shows unavailable rather than inventing meters.

## 10. Is the dashboard mocked?
**A:** Hackathon mode is DATA_MODE=energyplus. Missing results show energyplus_results_unavailable — no silent mock.

## 11. Is this deployed in a real building?
**A:** No. It controls an EnergyPlus digital building for verification.

## 12. Why was the aggressive policy not selected?
**A:** It increased savings but caused comfort violations; comfort-zero Path A is authoritative.

## 13. How is comfort calculated?
**A:** Occupied-hour zone temperatures versus band; violation hours and degree-hours independently recomputed.

## 14. How are savings calculated?
**A:** (baseline−agent)/baseline×100 on measured EnergyPlus meter totals.

## 15. How is carbon calculated?
**A:** Estimate: total_kWh × 0.417 kg/kWh — labeled estimate, not live grid intensity.

## 16. Are the results reproducible?
**A:** Yes from clean clone with the same IDF/EPW/scripts; Path A matches within rounding.

## 17. What prevents unsafe setpoints?
**A:** SafetyShield range, rate, deadband, and sensor/LLM/MCP health checks before actuation.

## 18. How would this connect to a real BMS?
**A:** Replace the EnergyPlus actuator adapter with a facility-approved BACnet/API connector behind the same SafetyShield.

## 19. What are the current limitations?
**A:** Digital-only, local Ollama, static carbon factor, sample model/weather, prototype security.

## 20. What would you build next?
**A:** BMS connector, multi-building validation, operator UX, and hardened auth/observability.
