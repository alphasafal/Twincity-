# Results — Baseline vs Agent (EnergyPlus)

## Methodology

Identical IDF, EPW, occupancy schedule family, and DemoPeriod within each scenario.
Controller is the only intentional difference. **No ×1.12 synthetic multiplier.**

Reproduction:

```bash
./scripts/run_baseline.sh && ./scripts/run_agent.sh && ./scripts/compare_results.sh
```

## Default scenario (comfort-zero tuned controller)

From `results/comparison/comparison.json` (post comfort hardening):

| Metric | Baseline | Agent | Reduction % |
|--------|----------|-------|-------------|
| Total energy (kWh) | 421.5057 | 415.9999 | **1.31%** |
| HVAC energy (kWh) | 13.8459 | 13.1570 | **4.98%** |
| Peak power (kW) | 19.9325 | 19.6400 | **1.47%** |
| Carbon estimate (kg) | 175.7679 | 173.5320 | 1.31% |
| Occupied comfort violation hours | 0.0 | **0.0** | — |
| Comfort degree-hours | 0.0 | **0.0** | — |

Agent actions: **48** approved, **0** rejected, **0** fallback.

### Comfort investigation (prior 1-hour violation)

Previous agent policy produced a single occupied overshoot:

| Field | Value |
|-------|-------|
| Timestamp | 07/15 10:00 |
| Zones | SPACE2-1, SPACE3-1 |
| Boundary | max 26.0 °C |
| Actual | ~26.22–26.24 °C |
| Max deviation | ~0.24 °C |
| Duration | 1 hour |
| Degree-hours | ~0.24 |

Controller updates (warning threshold, pre-cooling, occupied priority, rate limit) removed this violation while retaining HVAC energy improvement.

## LLM-via-MCP path

`./scripts/run_llm_mcp_experiment.sh` → `results/llm_mcp/`

- Stages logged in `stage_log.jsonl` (observation → MCP → LLM → SafetyShield → actuator)
- Ollama proposals that violate limits are **rejected** (example run: 32 rejected / 16 approved)
- `llm_bypass_possible: false`

## Multi-scenario

`./scripts/run_scenarios.sh` → `results/scenarios/consolidated_comparison.json`

Scenarios: `normal_summer`, `high_occupancy`, `hot_peak`.
