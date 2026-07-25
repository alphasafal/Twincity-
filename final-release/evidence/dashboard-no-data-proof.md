# Dashboard No-Data Proof

Generated: 2026-07-25T11:52:34.972235+00:00

## Method
1. Temporarily moved `results/baseline|agent|comparison` artifacts to untracked backup.
2. Queried status API with DATA_MODE=energyplus.
3. Restored artifacts.

## Observed (no artifacts)
- data_mode: `energyplus`
- data_label: `energyplus_results_unavailable`
- simulated: `False`
- synthetic_multiplier_applied: `False`
- energy_saved_today_pct: `None` (must be null)
- note: `No EnergyPlus experiment results found. Run the baseline and agent experiment scripts first. DATA_MODE=energyplus will not switch to mock automatically; set DATA_MODE=mock explicitly for mock development mode.`
- missing_artifacts: `['baseline/summary.json', 'agent/summary.json', 'comparison/comparison.json']`

## Checks
- Honest unavailable label: True
- Did not silently switch to mock: True
- No old metrics displayed: True
- After restore label: `energyplus_experiment_results` pct=`1.31`

## Verdict
**PASS**
