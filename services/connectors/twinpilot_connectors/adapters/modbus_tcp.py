"""Modbus TCP adapter (register-map driven).

Default transport is simulated. Set config transport=live + host/port to attempt
a Modbus TCP connect probe; register R/W uses the in-memory map unless a live
client library is installed.
"""

from __future__ import annotations

import socket
from datetime import UTC, datetime
from typing import Any

from twinpilot_connectors.base import ConnectorCapabilities, WriteRequest, WriteResult


class ModbusTCPAdapter:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.host = self.config.get("host", "127.0.0.1")
        self.port = int(self.config.get("port", 502))
        self.unit_id = int(self.config.get("unit_id", 1))
        self.transport = self.config.get("transport", "simulated")
        # register -> scaled engineering value
        self.register_map: dict[str, dict[str, Any]] = self.config.get("register_map") or {
            "40001": {"metric": "temperature", "scale": 0.1, "unit": "°C", "writable": False},
            "40002": {"metric": "cooling_setpoint", "scale": 0.1, "unit": "°C", "writable": True},
            "40003": {"metric": "power", "scale": 0.01, "unit": "kW", "writable": False},
        }
        self._raw: dict[str, int] = {k: 240 if "setpoint" in v["metric"] else 235 for k, v in self.register_map.items()}
        self._raw["40003"] = 4250
        self._reachable = True

    def health(self) -> dict[str, Any]:
        probe = None
        if self.transport == "live":
            probe = self._probe_tcp()
            self._reachable = bool(probe.get("reachable"))
        return {
            "status": "ok" if self._reachable else "offline",
            "provider": "modbus_tcp",
            "transport": self.transport,
            "host": self.host,
            "port": self.port,
            "unit_id": self.unit_id,
            "registers": len(self.register_map),
            "live_probe": probe,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _probe_tcp(self) -> dict[str, Any]:
        try:
            sock = socket.create_connection((self.host, self.port), timeout=0.5)
            sock.close()
            return {"reachable": True}
        except OSError as exc:
            return {"reachable": False, "reason": str(exc)}

    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            adapter_type="modbus_tcp",
            read=True,
            write=True,
            discover=True,
            vendor="generic_modbus",
        )

    def discover_points(self) -> list[dict[str, Any]]:
        points = []
        for reg, meta in self.register_map.items():
            points.append(
                {
                    "external_point_id": f"modbus://{self.unit_id}/{reg}",
                    "name": f"Register {reg} ({meta['metric']})",
                    "metric_hint": meta["metric"],
                    "unit": meta.get("unit", ""),
                    "writable": bool(meta.get("writable")),
                    "meta": {"register": reg, "scale": meta.get("scale", 1.0)},
                }
            )
        return points

    def poll_telemetry(self) -> list[dict[str, Any]]:
        now = datetime.now(UTC).isoformat()
        samples = []
        for reg, meta in self.register_map.items():
            scale = float(meta.get("scale", 1.0))
            samples.append(
                {
                    "external_point_id": f"modbus://{self.unit_id}/{reg}",
                    "metric": meta["metric"],
                    "value": self._raw.get(reg, 0) * scale,
                    "unit": meta.get("unit", ""),
                    "quality": "GOOD" if self._reachable else "STALE",
                    "timestamp_iso": now,
                }
            )
        return samples

    def write(self, request: WriteRequest) -> WriteResult:
        if self.transport == "live" and not self._reachable:
            return WriteResult(
                success=False,
                external_point_id=request.external_point_id,
                requested_value=request.value,
                detail="Modbus device unreachable — fail-safe",
                acked=False,
            )
        # external_point_id format: modbus://unit/register
        reg = request.external_point_id.rsplit("/", 1)[-1]
        meta = self.register_map.get(reg)
        if meta is None or not meta.get("writable"):
            return WriteResult(
                success=False,
                external_point_id=request.external_point_id,
                requested_value=request.value,
                detail="Register not writable or unknown",
                acked=False,
            )
        scale = float(meta.get("scale", 1.0)) or 1.0
        self._raw[reg] = int(round(request.value / scale))
        readback = self._raw[reg] * scale
        ok = abs(readback - request.value) <= max(request.deadband, abs(scale))
        return WriteResult(
            success=ok,
            external_point_id=request.external_point_id,
            requested_value=request.value,
            readback_value=readback,
            detail="modbus write ack",
            acked=ok,
        )

    def write_many(self, requests: list[WriteRequest]) -> list[WriteResult]:
        return [self.write(r) for r in requests]
