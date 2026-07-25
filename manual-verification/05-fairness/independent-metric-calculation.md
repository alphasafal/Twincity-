# Independent Metric Calculation

**Fresh baseline CSV mtime:** from run 2026-07-25T10:57:23Z  
**Fresh agent CSV mtime:** from run 2026-07-25T10:57:31Z  

## Independent extraction (from eplusout.csv meters)

| Metric | Baseline | Agent | Independent % reduction |
|--------|----------|-------|-------------------------|
| Total energy kWh | 421.5057 | 415.9999 | **1.3062** |
| HVAC energy kWh | 13.8459 | 13.157 | **4.9755** |
| Peak power kW | 19.9325 | 19.64 | **1.4675** |
| Comfort violation hours | 0.0 | 0.0 | — |
| Comfort degree-hours | 0.0 | 0.0 | — |

## Match vs application summary.json

| Check | Baseline | Agent |
|-------|----------|-------|
| total | True | True |
| hvac | True | True |
| peak | True | True |
| comfort hours | True | True |

## App percent_reduction (comparison.json)

- total: 1.3062
- hvac: 4.9755
- peak: 1.4675

Independent vs app deltas within rounding: total True
