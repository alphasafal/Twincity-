# Dashboard Data Lineage (Phase 12)

Report: `2026-07-25T11:08:07.584946+00:00`

## Path

`results/{baseline,agent,comparison}/*.json` → `experiment_store.experiment_dashboard_payload()` → `GET /buildings/{id}/status` → dashboard/`DataModeBanner`

## Fresh API vs raw

```json
{
  "data_mode": "energyplus",
  "data_mode_energyplus": true,
  "simulated_false": true,
  "no_multiplier": true,
  "baseline_total_api": 421.51,
  "baseline_total_raw_rounded": 421.51,
  "agent_total_api": 416.0,
  "agent_total_raw_rounded": 416.0,
  "baseline_total_match": true,
  "agent_total_match": true,
  "hvac_agent_match": true,
  "peak_match": true,
  "actions_approved": 48,
  "energy_saved_today_pct": 1.31,
  "reductions": {
    "total_energy_pct": 1.3062,
    "hvac_energy_pct": 4.9755,
    "peak_power_pct": 1.4675,
    "carbon_estimate_pct": 1.3062,
    "formula": "(baseline - agent) / baseline * 100"
  }
}
```

**VERIFIED** when artifacts present. **FAILED** silent-mock-on-missing (Phase 12 failure doc).
