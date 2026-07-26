# Closed-Loop Trace — EnergyPlus Eco-Loop

**Audit date:** 2026-07-25  
**Proof commands:** `./scripts/run_baseline.sh && ./scripts/run_agent.sh && ./scripts/compare_results.sh`  
**Evidence artifacts:** `results/baseline/summary.json`, `results/agent/summary.json`, `results/comparison/comparison.json`

---

## Control cycle (agent experiment)

```text
EnergyPlus Runtime timestep
  → read Zone Air Temperature / occupancy / outdoor drybulb
  → deterministic agent proposal (cooling setpoint)
  → deterministic safety validation (range, rate, deadband, sensors, infra)
  → if approved: set Schedule:Compact actuator Clg-SetP-Sch
  → EnergyPlus advances HVAC with injected setpoint
  → next timestep observations
  → post-run CSV meters → summary JSON → comparison
```

Interactive TwinPilot API/dashboard closed loop still defaults to the **mock twin**
(`SIMULATOR_PROVIDER=mock`). The **measured** EnergyPlus closed loop is the experiment harness.

---

## Field provenance

| Signal | Source | Transform | Mocked? |
|--------|--------|-----------|---------|
| Zone temperature | EnergyPlus variable `Zone Air Temperature` per `SPACE*-1` | Runtime API `get_variable_value` | **No** |
| Occupancy | EnergyPlus `Zone People Occupant Count` / `People Occupant Count` | Runtime API | **No** (handles require Output:Variable in IDF) |
| Energy usage | `eplusout.csv` meters `Electricity:Facility`, `Electricity:HVAC`, etc. | J → kWh (`/ 3.6e6`) | **No** |
| Weather | `building-models/weather/chicago.epw` (Chicago TMY3) | EnergyPlus weather reader | **No** (standard EPW file) |
| Carbon | `total_energy_kwh * 0.417` | Documented estimate factor | **Derived estimate** (not live grid) |
| Agent input | outdoor, zone temps, occupancy, current cooling SP | Python dict in callback | Real E+ observations |
| Agent output schema | `{proposed_cooling_setpoint_c, reason, confidence}` | Deterministic policy | Not LLM-direct |
| Safety validation | `validate_setpoint_action` + `SafetyShield` checks | Hard rejects / fallback hold | Deterministic |
| Setpoint injection | Actuator `Schedule:Compact` / `Schedule Value` / `Clg-SetP-Sch` | `set_actuator_value` | **No** |
| E+ acceptance | `energyplus_action_accepted` in `actions.json`; nonzero energy deltas vs baseline | Run comparison | Proven by results |
| New simulation state | Subsequent timestep temps / meters | EnergyPlus physics | **No** |
| Dashboard update | API KPI endpoints (mock demo) / `results/*` for measured | See dashboard lineage | Mock KPIs labeled |
| Audit log | `results/agent/actions.json` + API `AuditEvent` for mock demo | JSON / SQLite | Experiment log is real |

---

## P0 fixes applied

1. Replaced silent EnergyPlus→mock delegation with `ep_experiment.run_experiment` Runtime API loop.
2. Added IDF `office_5zone.idf` + EPW `chicago.epw` with short `DemoPeriod` (Jul 15–16).
3. Strict mode: `EnergyPlusAdapter` raises `EnergyPlusUnavailableError` unless `ENERGYPLUS_ALLOW_MOCK_FALLBACK=1`.
4. Experiment scripts refuse to invent success when EnergyPlus is missing (exit ≠ 0).

---

## Measured sample (this environment)

See `results/comparison/comparison.json` after running the scripts (comfort-zero tuned):

- Baseline total energy ≈ **421.51 kWh**
- Agent total energy ≈ **416.00 kWh** (**1.31%** reduction)
- HVAC energy ≈ **4.98%** reduction
- Peak power ≈ **1.47%** reduction
- Occupied comfort violation hours: **0** / **0** degree-hours
- Agent decisions: **48** approved / 0 rejected / 0 fallback
- Dashboard default: `DATA_MODE=energyplus` (no ×1.12)
