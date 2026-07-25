# Experiment Fairness Check

Generated: 2026-07-25T11:44:51.624870+00:00

Fresh Path A baseline vs agent — controller is the intended difference.

## Shared inputs

| Item | Baseline | Agent | Match |
|---|---|---|---|
| IDF path | `None` | `None` | YES |
| EPW path | `None` | `None` | YES |
| IDF sha256 | `b7a60565284197c2ee67d36a85642a46b5669579ce2dd14e96bf99736aaca77b` | `b7a60565284197c2ee67d36a85642a46b5669579ce2dd14e96bf99736aaca77b` | YES |
| EPW sha256 | `3cc3dc0c7bcc93e7203e8d9aab657d384315f5a0c86cdede23f792d437a0309f` | `3cc3dc0c7bcc93e7203e8d9aab657d384315f5a0c86cdede23f792d437a0309f` | YES |
| EnergyPlus version | `None` | `None` | YES |
| EnergyPlus home | `/workspace/third_party/EnergyPlus` | `/workspace/third_party/EnergyPlus` | YES |
| identical_inputs.epw | `/workspace/building-models/weather/chicago.epw` | `/workspace/building-models/weather/chicago.epw` | YES |
| identical_inputs.idf | `/workspace/building-models/sample-office/office_5zone.idf` | `/workspace/building-models/sample-office/office_5zone.idf` | YES |
| identical_inputs.occupancy_schedule | `OCCUPY-1 (unchanged between experiments)` | `OCCUPY-1 (unchanged between experiments)` | YES |
| identical_inputs.run_period | `DemoPeriod 07/15-07/16 (patched in IDF)` | `DemoPeriod 07/15-07/16 (patched in IDF)` | YES |
| scenario | `default` | `default` | YES |
| schema_version | `1.0` | `1.0` | YES |

## Intentional differences

- Baseline controller: `none`
- Agent controller: `deterministic+safety_shield`
- Baseline decisions: `0`
- Agent decisions: `48`

## Verdict

**VALID** — inputs match; only the controller/actuator path differs.
