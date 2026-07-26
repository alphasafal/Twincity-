# Carbon accounting (estimate)

## Label

All carbon figures in TwinPilot / Eco-Loop are **estimates**, not measured grid emissions.

## Formula

```text
carbon_estimate_kg = total_energy_kwh × emission_factor_kg_per_kwh
```

Percent reduction (when shown):

```text
carbon_reduction_pct = (baseline_kg - agent_kg) / baseline_kg × 100
```

## Emission factor

| Item | Value |
|------|-------|
| Symbol | `DEFAULT_CARBON_KG_PER_KWH` |
| Default | **0.417 kg CO2e / kWh** |
| Config | `ExperimentConfig.carbon_kg_per_kwh` / summary field `carbon_factor_kg_per_kwh` |
| Source / configuration | Documented demo factor in `ep_experiment.py`; overridable per experiment |
| Units | **kg CO2e (estimate)** |

## Limitations

1. Not live locational marginal emissions or utility-reported intensity  
2. Single static factor applied to facility electricity only  
3. Excludes refrigerants, embodied carbon, and district energy  
4. Suitable for relative baseline-vs-agent comparison, not regulatory reporting  

## Where shown

- `results/*/summary.json` → `carbon_estimate_kg` + `carbon_note`
- Dashboard / analytics when `DATA_MODE=energyplus` (labeled estimate)
- `submission-evidence/comparison.json` → `carbon_accounting`
