# Dashboard Data Lineage

**Audit date:** 2026-07-25  
**Scope:** TwinPilot web operator dashboard metrics and charts.

---

## Summary

| Surface | Real? | Notes |
|---------|-------|-------|
| Live zone temperatures / power (default demo) | **Mock twin** | `MockBuildingSimulator` dynamics |
| Energy saved % on status cards (default demo) | **Synthetic derived** | `baseline_power = power * 1.12` heuristic — labeled |
| Measured EnergyPlus baseline vs agent | **Real** | Not plotted live; use `results/comparison/` |
| Alerts / decisions / audit | **Real DB rows** | SQLite/Postgres via API |
| Comfort compliance | **Derived from mock zone status** | Or EnergyPlus violation hours in experiment JSON |

---

## Card / chart lineage

| UI element | Source API | DB / engine | Update frequency | Unit | Fallback | Classification |
|------------|------------|-------------|------------------|------|----------|----------------|
| Building mode | `GET /buildings/{id}/status` | `buildings.current_mode` | on poll / WS | enum | last known | Real config |
| Live total load | status → `state.total_building_power_kw` | simulator state | control interval (~5s) | kW | null if no state | Mock (default) / E+ peak if energyplus init |
| Energy saved today % | status `energy_saved_today_pct` | RuntimeHub KPI counters | each KPI snapshot | % | 0 | **Synthetic** when `simulated=true` |
| Cost saved | status `cost_saved_today` | RuntimeHub | each snapshot | currency units | 0 | Synthetic vs mock baseline |
| Carbon avoided | status `carbon_avoided_today_kg` | RuntimeHub | each snapshot | kg | 0 | Synthetic |
| Peak reduction % | status `peak_demand_reduction_pct` | RuntimeHub | each snapshot | % | 0 | Synthetic (mock only) |
| Comfort compliance % | status `comfort_compliance_pct` | RuntimeHub from zone comfort_status | each snapshot | % | seeded 96.4 | Derived mock |
| Healthy sensors % | status computed from zone `sensor_health` | simulator state | poll | % | 0 | Mock / adapter |
| Active alerts | status count | `alerts` table | poll | count | 0 | Real DB |
| Pending decisions | status count | `decisions` table | poll | count | 0 | Real DB |
| KPI history chart | status `kpi_history` / analytics timeseries | RuntimeHub memory | each snapshot | kW / % | empty | Mock-labeled |
| Zone cards | `GET /buildings/{id}/zones` + live state | `zones` + simulator | poll / WS | °C, etc. | DB last | Mock telemetry default |
| Digital twin | state endpoint | simulator | poll | mixed | — | Mock unless energyplus |
| Analytics summary | `GET .../analytics/summary` | RuntimeHub | poll | mixed | 0 | Labeled `mock_twin_demo_kpis` |
| Prediction ledger | ledger endpoints | `prediction_ledger` | on apply | mixed | — | Real DB; values from sim |
| Assistant answers | `/assistant/chat` | agent provider | on demand | text | deterministic | Deterministic or Ollama |
| Service health | status `service_health` | RuntimeHub dict | poll | enum | ok | Mostly process-local flags |

API now returns `simulated` from `hub.latest_state.simulated` (not hardcoded `true`) and `data_label`.

---

## Fake / synthetic values removed or labeled

1. Hardcoded `"simulated": True` on status/state → now reflects simulator state.
2. Analytics `label: "simulated"` → `mock_twin_demo_kpis` or `energyplus_live_state`.
3. Synthetic 1.12 baseline factor → applied only when `state.simulated` is true; documented in KPI `baseline_method`.
4. EnergyPlus experiment metrics are the **authoritative** savings evidence (`results/comparison/comparison.json`).

---

## Evaluator guidance

- Do **not** quote dashboard “energy saved today %” as EnergyPlus proof.
- Quote `results/comparison/comparison.json` percentages produced by `./scripts/compare_results.sh`.
