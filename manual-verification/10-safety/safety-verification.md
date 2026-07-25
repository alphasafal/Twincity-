# SafetyShield Verification (Phase 10)

Report: `2026-07-25T11:08:07.584946+00:00`

## Two gates

1. **Experiment gate:** `ep_experiment.validate_setpoint_action`
2. **Optimizer shield:** `SafetyShield.validate`

## Matrix

See `safety-test-matrix.csv` — **35 cases, 35 passed**.

Limits used by experiment gate: {"min_cooling_setpoint": 22.0, "max_cooling_setpoint": 28.0, "min_heating_setpoint": 16.0, "max_heating_setpoint": 24.0, "max_setpoint_change_per_interval": 1.0, "heating_cooling_deadband_c": 1.5, "comfort_occupied_min_c": 21.0, "comfort_occupied_max_c": 26.0, "comfort_warning_c": 25.3, "max_occupied_cooling_setpoint": 24.8, "max_unoccupied_cooling_setpoint": 25.8, "max_sensor_temperature_c": 50.0, "min_sensor_temperature_c": 0.0, "max_data_age_seconds": 900.0}

## Unsafe demo (runtime)

`results/llm_mcp/stage_log.jsonl`: proposed 35.0 → rejected (`cooling_setpoint_out_of_range`, `max_setpoint_change_exceeded`).

## Unit tests

21 passed (`test_ep_experiment_safety.py` + `test_safety_failure_modes.py`).
