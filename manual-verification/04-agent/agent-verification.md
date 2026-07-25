# Agent Verification (Phase 4)

- Report time: `2026-07-25T11:07:18.441284+00:00`
- Command: `./scripts/run_agent.sh`
- Meta: start `2026-07-25T10:57:30Z`, exit `0`, ~1s wall / EnergyPlus ~0.29s
- Controller: `deterministic+safety_shield` (**deterministic**, not LLM — separate from Path B)

## Metrics

| Metric | App | Independent |
|--------|-----|-------------|
| Total energy kWh | 415.9999 | 415.9999 |
| HVAC energy kWh | 13.157 | 13.157 |
| Peak power kW | 19.64 | 19.64 |
| Comfort hours | 0.0 | 0.0 |
| Actions | {'approved': 48, 'rejected': 0, 'fallback': 0, 'total_decisions': 48} | {'total_rows': 48, 'approved': 48, 'rejected': 0, 'fallback': 0, 'unique_timestamps': 48, 'duplicate_timestamps': 0, 'monotonic_sorted': True} |

## EnergyPlus health

0 Warning / 0 Severe / 0 Fatal (`err-scan.txt`)

## Freshness

- `timestamp_utc`: `2026-07-25T10:57:31.054476+00:00`
- Actions file rows: 48
- Distinct from baseline energy (415.9999 vs 421.5057)

## Status

**VERIFIED** for deterministic agent path. LLM controller results are under Phase 9 / `results/llm_mcp/` and must not be conflated.
