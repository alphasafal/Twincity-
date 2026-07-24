"""Connector protocols — TelemetrySource + ActuatorSink."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class DiscoveredPoint(BaseModel):
    external_point_id: str
    name: str
    metric_hint: str = "unknown"
    unit: str = ""
    writable: bool = False
    meta: dict[str, Any] = Field(default_factory=dict)


class TelemetrySample(BaseModel):
    external_point_id: str
    metric: str
    value: float
    unit: str = ""
    quality: str = "GOOD"
    zone_id: str | None = None
    timestamp_iso: str | None = None


class WriteRequest(BaseModel):
    external_point_id: str
    value: float
    deadband: float = 0.1
    unit: str = ""
    meta: dict[str, Any] = Field(default_factory=dict)


class WriteResult(BaseModel):
    success: bool
    external_point_id: str
    requested_value: float
    readback_value: float | None = None
    detail: str = ""
    acked: bool = False


class ConnectorCapabilities(BaseModel):
    adapter_type: str
    read: bool = True
    write: bool = False
    discover: bool = True
    vendor: str = "generic"


@runtime_checkable
class TelemetrySource(Protocol):
    def health(self) -> dict[str, Any]: ...

    def capabilities(self) -> ConnectorCapabilities: ...

    def discover_points(self) -> list[dict[str, Any]]: ...

    def poll_telemetry(self) -> list[dict[str, Any]]: ...


@runtime_checkable
class ActuatorSink(Protocol):
    def write(self, request: WriteRequest) -> WriteResult: ...

    def write_many(self, requests: list[WriteRequest]) -> list[WriteResult]: ...
