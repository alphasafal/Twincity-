# Baseline vs Agent Comparison

- Generated: 
- Inputs identical: **True**

| Metric | Baseline | Agent | Δ (agent−baseline) | % |
|--------|----------|-------|--------------------|---|
| Total energy (kWh) | 421.5057 | 415.9999 | -5.5058 | -1.3062% |
| HVAC energy (kWh) | 13.8459 | 13.157 | -0.6889 | -4.9755% |
| Peak power (kW) | 19.9325 | 19.64 | -0.2925 | -1.4675% |
| Carbon estimate (kg) | 175.7679 | 173.472 | -2.2959 | -1.3062% |
| Occupied comfort violation hours | 0.0 | 0.0 | 0.0 | n/a |

## Agent actions


## Notes
- percent_reduction = (baseline - agent) / baseline * 100 (positive means agent used less).
- Carbon values are estimates using a documented kg/kWh factor.
- Only controller differs: baseline has no setpoint overrides; agent uses SafetyShield-gated overrides.
- Synthetic multipliers (e.g. ×1.12) are not used.
