# Baseline Verification (Phase 3)

- ISO timestamp (report): `2026-07-25T11:07:18.441284+00:00`
- Tested HEAD at experiment time: `589643c3557c56922b79edd886e88ea9e6833474` (Phase 0 freeze was `61ed36cc9bc89cd37ba7a38a1ec7b4d1e12702e1`; only docs/audit map changed)
- Command: `./scripts/run_baseline.sh`
- Meta: see `run-meta.txt` — start `2026-07-25T10:57:23Z`, exit `0`, duration ~0–1s wall (EnergyPlus reports 0.28s elapsed for this short 5-zone DemoPeriod)
- Pre-audit archive: `manual-verification/archives/results-pre-audit-20260725T105438Z/`
- Fresh outputs copied under `fresh-run/` and mirrored in `results/baseline/`

## EnergyPlus health

- `eplusout.err` scan: **0 Warning, 0 Severe, 0 Fatal** (`err-scan.txt`)
- Runtime log: EnergyPlus 24.1.0 completed successfully

## Independent extraction (from `eplusout.csv`)

| Metric | App summary | Independent |
|--------|-------------|-------------|
| Total energy kWh | 421.5057 | 421.5057 |
| HVAC energy kWh | 13.8459 | 13.8459 |
| Peak power kW | 19.9325 | 19.9325 |
| Comfort violation hours | 0.0 | 0.0 |
| Comfort degree-hours | 0.0 | 0.0 |

## Provenance

- IDF: `/workspace/building-models/sample-office/office_5zone.idf`
- EPW: `/workspace/building-models/weather/chicago.epw`
- Period: `DemoPeriod 07/15-07/16 (patched in IDF)`
- Occupancy: `OCCUPY-1 (unchanged between experiments)`
- Controller: `none`
- Freshness: `summary.json` timestamp `2026-07-25T11:06:17.981037+00:00`; eplusout.csv mtime 2026-07-25 10:57:23Z

## Status

**VERIFIED** — fresh baseline artifacts generated; independent meter sums match app summary.
