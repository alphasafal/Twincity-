# Failure Injection Analysis (Phase 11)

Report: `2026-07-25T11:08:07.584946+00:00`

Summary: {"total": 15, "passed": 14, "failed": ["silent_mock_when_energyplus_missing_results"]}

## Highlights

- Ollama unavailable/wrong endpoint/missing model → deterministic_fallback stages logged (proven)
- EnergyPlus missing / bad IDF / bad EPW → non-zero exit (hard fail)
- Missing results → experiment.available=false
- Corrupt comparison → null comparison, listed missing
- **P0:** DATA_MODE=energyplus with missing results → router falls through to mock-labeled status
- Real MCP down/timeout → N/A (not wired)
- Permission denied on results dir → exit 1
