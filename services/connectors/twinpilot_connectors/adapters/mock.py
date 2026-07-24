"""Mock connector adapting the in-process simulator contract for commissioning."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from twinpilot_connectors.base import (
    ConnectorCapabilities,
    WriteRequest,
    WriteResult,
)


class MockConnectorAdapter:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self._setpoints: dict[str, float] = {
            "mock://core/cooling_setpoint": 24.0,
            "mock://north/cooling_setpoint": 24.0,
            "mock://south/cooling_setpoint": 24.5,
            "mock://east/cooling_setpoint": 24.0,
            "mock://west/cooling_setpoint": 24.0,
        }
        self._last_ok = True

    def health(self) -> dict[str, Any]:
        return {
            "status": "ok" if self._last_ok else "degraded",
            "provider": "mock",
            "simulated": True,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            adapter_type="mock",
            read=True,
            write=True,
            discover=True,
            vendor="twinpilot",
        )

    def discover_points(self) -> list[dict[str, Any]]:
        zones = ["core", "north", "south", "east", "west"]
        points: list[dict[str, Any]] = []
        for z in zones:
            for metric, unit, writable in [
                ("temperature", "°C", False),
                ("humidity", "%", False),
                ("co2", "ppm", False),
                ("occupancy", "count", False),
                ("power", "kW", False),
                ("cooling_setpoint", "°C", True),
            ]:
                points.append(
                    {
                        "external_point_id": f"mock://{z}/{metric}",
                        "name": f"{z} {metric}",
                        "metric_hint": metric,
                        "unit": unit,
                        "writable": writable,
                        "meta": {"zone_key": z},
                    }
                )
        return points

    def poll_telemetry(self) -> list[dict[str, Any]]:
        now = datetime.now(UTC).isoformat()
        samples: list[dict[str, Any]] = []
        for z in ["core", "north", "south", "east", "west"]:
            samples.append(
                {
                    "external_point_id": f"mock://{z}/temperature",
                    "metric": "temperature",
                    "value": 24.2,
                    "unit": "°C",
                    "quality": "GOOD",
                    "timestamp_iso": now,
                }
            )
            samples.append(
                {
                    "external_point_id": f"mock://{z}/cooling_setpoint",
                    "metric": "cooling_setpoint",
                    "value": self._setpoints.get(f"mock://{z}/cooling_setpoint", 24.0),
                    "unit": "°C",
                    "quality": "GOOD",
                    "timestamp_iso": now,
                }
            )
        samples.append(
            {
                "external_point_id": "mock://building/power",
                "metric": "total_building_power_kw",
                "value": 42.5,
                "unit": "kW",
                "quality": "GOOD",
                "timestamp_iso": now,
            }
        )
        return samples

    def write(self, request: WriteRequest) -> WriteResult:
        self._setpoints[request.external_point_id] = request.value
        readback = self._setpoints[request.external_point_id]
        ok = abs(readback - request.value) <= max(request.deadband, 0.01)
        self._last_ok = ok
        return WriteResult(
            success=ok,
            external_point_id=request.external_point_id,
            requested_value=request.value,
            readback_value=readback,
            detail="mock write ack",
            acked=ok,
        )

    def write_many(self, requests: list[WriteRequest]) -> list[WriteResult]:
        return [self.write(r) for r in requests]
