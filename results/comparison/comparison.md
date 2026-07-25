# Baseline vs Agent Comparison

- Generated: 
- Inputs identical: **True**

| Metric | Baseline | Agent | Δ (agent−baseline) | % |
|--------|----------|-------|--------------------|---|
| Total energy (kWh) | 421.5057 | 406.2102 | -15.2955 | -3.6288% |
| HVAC energy (kWh) | 13.8459 | 12.1566 | -1.6893 | -12.2007% |
| Peak power (kW) | 19.9325 | 19.4989 | -0.4336 | -2.1753% |
| Carbon estimate (kg) | 175.7679 | 169.3897 | -6.3782 | -3.6288% |
| Occupied comfort violation hours | 0.0 | 1.0 | 1.0 | n/a |

## Agent actions


## Notes
- Negative absolute_delta means agent used less than baseline.
- Carbon values are estimates using a documented kg/kWh factor.
- Only controller differs: baseline has no setpoint overrides; agent uses SafetyShield-gated overrides.
