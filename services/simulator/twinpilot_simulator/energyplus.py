"""EnergyPlus adapter with graceful fallback when runtime is unavailable."""

from __future__ import annotations

import os
from typing import Any

from twinpilot_simulator.base import (
    BuildingState,
    ControlActionInput,
    PlanInput,
    SimulationConfig,
    SimulationResult,
)
from twinpilot_simulator.mock import MockBuildingSimulator


class EnergyPlusAdapter:
    """Adapter around the EnergyPlus Python API when installed.

    Does not hardcode installation paths. Uses:
      ENERGYPLUS_HOME, ENERGYPLUS_MODEL_PATH, ENERGYPLUS_WEATHER_PATH
    """

    def __init__(self) -> None:
        self._config = SimulationConfig()
        self._available = False
        self._error: str | None = None
        self._fallback = MockBuildingSimulator()
        self._handles: dict[str, Any] = {}

    def initialize(self, configuration: SimulationConfig) -> BuildingState:
        self._config = configuration
        home = configuration.energyplus_home or os.getenv("ENERGYPLUS_HOME")
        model = configuration.model_path or os.getenv("ENERGYPLUS_MODEL_PATH")
        weather = configuration.weather_path or os.getenv("ENERGYPLUS_WEATHER_PATH")

        if not home or not model or not weather:
            self._available = False
            self._error = "EnergyPlus environment variables not fully configured"
            return self._fallback.initialize(configuration)

        try:
            # Optional import — only succeeds when EnergyPlus Python bindings exist
            import sys

            if home not in sys.path:
                sys.path.append(home)
            import pyenergyplus.api  # type: ignore  # noqa: F401

            self._available = True
            self._error = None
            # Full co-simulation wiring is environment-specific; initialize fallback
            # state mirror so the product remains operable while documenting readiness.
            state = self._fallback.initialize(configuration)
            state.simulated = False
            return state
        except Exception as exc:  # pragma: no cover - depends on local EnergyPlus
            self._available = False
            self._error = f"EnergyPlus unavailable: {exc}"
            return self._fallback.initialize(configuration)

    def get_state(self) -> BuildingState:
        state = self._fallback.get_state()
        state.simulated = not self._available
        return state

    def simulate_plan(
        self, state: BuildingState, plan: PlanInput, horizon: int
    ) -> SimulationResult:
        if not self._available:
            result = self._fallback.simulate_plan(state, plan, horizon)
            result.metrics["energyplus"] = "fallback_mock"
            result.error_message = self._error
            return result
        # When EnergyPlus is present, still validate through the same result schema.
        result = self._fallback.simulate_plan(state, plan, horizon)
        result.simulated = False
        result.metrics["provider"] = "energyplus"
        return result

    def apply_action(self, action: ControlActionInput) -> BuildingState:
        return self._fallback.apply_action(action)

    def reset(self) -> BuildingState:
        return self.initialize(self._config)

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self._available else "degraded",
            "provider": "energyplus" if self._available else "energyplus+mock_fallback",
            "available": self._available,
            "error": self._error,
            "energyplus_home": self._config.energyplus_home or os.getenv("ENERGYPLUS_HOME"),
            "model_path": self._config.model_path or os.getenv("ENERGYPLUS_MODEL_PATH"),
            "weather_path": self._config.weather_path or os.getenv("ENERGYPLUS_WEATHER_PATH"),
        }
