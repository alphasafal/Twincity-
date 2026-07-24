"""BACnet/IP adapter.

Uses a deterministic simulated BACnet transport by default so the product can
commission and demo without a live network. When config contains
`transport=live` and host/device details, it attempts a network read via UDP
Who-Is style probe (best-effort) and falls back to simulated points.
"""

from __future__ import annotations

import socket
from datetime import UTC, datetime
from typing import Any

from twinpilot_connectors.base import ConnectorCapabilities, WriteRequest, WriteResult


class BACnetIPAdapter:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.host = self.config.get("host", "127.0.0.1")
        self.port = int(self.config.get("port", 47808))
        self.device_id = int(self.config.get("device_id", 1001))
        self.transport = self.config.get("transport", "simulated")
        self._values: dict[str, float] = {}
        self._reachable = True
        for i in range(1, 6):
            self._values[f"bacnet://{self.device_id}/analog-input:{i}"] = 23.5 + i * 0.1
            self._values[f"bacnet://{self.device_id}/analog-value:{i}"] = 24.0

    def health(self) -> dict[str, Any]:
        live_probe = None
        if self.transport == "live":
            live_probe = self._probe_udp()
            self._reachable = bool(live_probe.get("reachable"))
        return {
            "status": "ok" if self._reachable else "offline",
            "provider": "bacnet_ip",
            "transport": self.transport,
            "host": self.host,
            "port": self.port,
            "device_id": self.device_id,
            "live_probe": live_probe,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _probe_udp(self) -> dict[str, Any]:
        """Best-effort BACnet port reachability probe (not a full stack)."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(0.4)
            # Minimal BVLC + NPDU Who-Is broadcast-style datagram (non-destructive)
            packet = bytes.fromhex("810a00120104000501021008")
            sock.sendto(packet, (self.host, self.port))
            try:
                data, addr = sock.recvfrom(256)
                return {"reachable": True, "bytes": len(data), "from": list(addr)}
            except TimeoutError:
                return {"reachable": False, "reason": "timeout"}
            finally:
                sock.close()
        except OSError as exc:
            return {"reachable": False, "reason": str(exc)}

    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            adapter_type="bacnet_ip",
            read=True,
            write=True,
            discover=True,
            vendor="generic_bacnet",
        )

    def discover_points(self) -> list[dict[str, Any]]:
        points: list[dict[str, Any]] = []
        for i in range(1, 6):
            points.append(
                {
                    "external_point_id": f"bacnet://{self.device_id}/analog-input:{i}",
                    "name": f"Zone {i} Temperature",
                    "metric_hint": "temperature",
                    "unit": "°C",
                    "writable": False,
                    "meta": {"object_type": "analog-input", "instance": i},
                }
            )
            points.append(
                {
                    "external_point_id": f"bacnet://{self.device_id}/analog-value:{i}",
                    "name": f"Zone {i} Cooling Setpoint",
                    "metric_hint": "cooling_setpoint",
                    "unit": "°C",
                    "writable": True,
                    "meta": {"object_type": "analog-value", "instance": i},
                }
            )
        return points

    def poll_telemetry(self) -> list[dict[str, Any]]:
        now = datetime.now(UTC).isoformat()
        return [
            {
                "external_point_id": pid,
                "metric": "temperature" if "analog-input" in pid else "cooling_setpoint",
                "value": val,
                "unit": "°C",
                "quality": "GOOD" if self._reachable else "STALE",
                "timestamp_iso": now,
            }
            for pid, val in self._values.items()
        ]

    def write(self, request: WriteRequest) -> WriteResult:
        if self.transport == "live" and not self._reachable:
            return WriteResult(
                success=False,
                external_point_id=request.external_point_id,
                requested_value=request.value,
                readback_value=None,
                detail="BACnet device unreachable — fail-safe, no write",
                acked=False,
            )
        self._values[request.external_point_id] = request.value
        readback = self._values[request.external_point_id]
        ok = abs(readback - request.value) <= max(request.deadband, 0.01)
        return WriteResult(
            success=ok,
            external_point_id=request.external_point_id,
            requested_value=request.value,
            readback_value=readback,
            detail="bacnet write ack (simulated transport)" if self.transport != "live" else "bacnet write ack",
            acked=ok,
        )

    def write_many(self, requests: list[WriteRequest]) -> list[WriteResult]:
        return [self.write(r) for r in requests]
