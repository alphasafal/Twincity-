# Experiment Input Comparison

**Tested commit:** `61ed36cc9bc89cd37ba7a38a1ec7b4d1e12702e1`

| Item | Baseline | Agent | Match? |
|------|----------|-------|--------|
| IDF path | /workspace/building-models/sample-office/office_5zone.idf | /workspace/building-models/sample-office/office_5zone.idf | True |
| IDF sha256 | `b7a60565284197c2ee67d36a85642a46b5669579ce2dd14e96bf99736aaca77b` | same file | YES |
| EPW path | /workspace/building-models/weather/chicago.epw | /workspace/building-models/weather/chicago.epw | YES |
| EPW sha256 | `3cc3dc0c7bcc93e7203e8d9aab657d384315f5a0c86cdede23f792d437a0309f` | same file | YES |
| Run period | DemoPeriod 07/15-07/16 (patched in IDF) | DemoPeriod 07/15-07/16 (patched in IDF) | YES |
| Occupancy schedule | OCCUPY-1 (unchanged between experiments) | OCCUPY-1 (unchanged between experiments) | YES |
| Controller | `none` | `deterministic+safety_shield` | **INTENDED DIFFERENCE** |
| EnergyPlus version | 24.1.0-9d7789a3ac | same binary | YES |

Both runs completed with 0 Severe / 0 Fatal errors.
