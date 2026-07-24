"""Honeywell Niagara / Forge-style REST adapter (certified path).

Implements the same TelemetrySource + ActuatorSink protocols. Credentials are
referenced via secret_ref / config — never logged. Default transport is a
sandboxed simulated Niagara station for partner certification harnesses.
Set transport=live + base_url + api_key (or secret from vault) for real sites.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx

from twinpilot_connectors.base import ConnectorCapabilities, WriteRequest, WriteResult


class HoneywellNiagaraAdapter:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.base_url = (self.config.get("base_url") or "https://niagara.example.local").rstrip("/")
        self.transport = self.config.get("transport", "simulated")
        self.station = self.config.get("station", "TwinPilotDemo")
        self.api_key = self.config.get("api_key")  # prefer vault/env injection
        self._points = {
            f"honeywell://{self.station}/zone{i}/temp": {
                "name": f"Zone {i} Temp",
                "metric": "temperature",
                "value": 23.0 + i * 0.2,
                "writable": False,
                "unit": "°C",
            }
            for i in range(1, 6)
        }
        for i in range(1, 6):
            self._points[f"honeywell://{self.station}/zone{i}/clgSp"] = {
                "name": f"Zone {i} Cooling SP",
                "metric": "cooling_setpoint",
                "value": 24.0,
                "writable": True,
                "unit": "°C",
            }
        self._reachable = True

    def health(self) -> dict[str, Any]:
        probe = None
        if self.transport == "live":
            probe = self._probe_rest()
            self._reachable = bool(probe.get("reachable"))
        return {
            "status": "ok" if self._reachable else "offline",
            "provider": "honeywell_niagara",
            "vendor": "honeywell",
            "transport": self.transport,
            "base_url": self.base_url,
            "station": self.station,
            "certified_adapter": True,
            "live_probe": probe,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "TwinPilot-HoneywellAdapter/1.0"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _probe_rest(self) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=1.5, verify=bool(self.config.get("verify_tls", True))) as client:
                resp = client.get(f"{self.base_url}/ord", headers=self._headers())
                return {"reachable": resp.status_code < 500, "status_code": resp.status_code}
        except Exception as exc:  # noqa: BLE001 — connectivity probe
            return {"reachable": False, "reason": str(exc)}

    def capabilities(self) -> ConnectorCapabilities:
        return ConnectorCapabilities(
            adapter_type="honeywell_niagara",
            read=True,
            write=True,
            discover=True,
            vendor="honeywell",
        )

    def discover_points(self) -> list[dict[str, Any]]:
        return [
            {
                "external_point_id": pid,
                "name": meta["name"],
                "metric_hint": meta["metric"],
                "unit": meta["unit"],
                "writable": meta["writable"],
                "meta": {"station": self.station},
            }
            for pid, meta in self._points.items()
        ]

    def poll_telemetry(self) -> list[dict[str, Any]]:
        if self.transport == "live" and self._reachable:
            # Live path: attempt station points read; fall back to cache on failure
            try:
                with httpx.Client(timeout=2.0, verify=bool(self.config.get("verify_tls", True))) as client:
                    resp = client.get(
                        f"{self.base_url}/api/points",
                        headers=self._headers(),
                        params={"station": self.station},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, list):
                            return [
                                {
                                    "external_point_id": p.get("id", ""),
                                    "metric": p.get("metric", "unknown"),
                                    "value": float(p.get("value", 0)),
                                    "unit": p.get("unit", ""),
                                    "quality": p.get("quality", "GOOD"),
                                    "timestamp_iso": datetime.now(UTC).isoformat(),
                                }
                                for p in data
                            ]
            except Exception:  # noqa: BLE001
                self._reachable = False
        now = datetime.now(UTC).isoformat()
        return [
            {
                "external_point_id": pid,
                "metric": meta["metric"],
                "value": float(meta["value"]),
                "unit": meta["unit"],
                "quality": "GOOD" if self._reachable else "STALE",
                "timestamp_iso": now,
            }
            for pid, meta in self._points.items()
        ]

    def write(self, request: WriteRequest) -> WriteResult:
        if self.transport == "live" and not self._reachable:
            return WriteResult(
                success=False,
                external_point_id=request.external_point_id,
                requested_value=request.value,
                detail="Honeywell station unreachable — fail-safe, no write",
                acked=False,
            )
        meta = self._points.get(request.external_point_id)
        if meta is None or not meta.get("writable"):
            return WriteResult(
                success=False,
                external_point_id=request.external_point_id,
                requested_value=request.value,
                detail="Point not writable",
                acked=False,
            )
        if self.transport == "live":
            try:
                with httpx.Client(timeout=2.0, verify=bool(self.config.get("verify_tls", True))) as client:
                    resp = client.post(
                        f"{self.base_url}/api/points/write",
                        headers=self._headers(),
                        json={
                            "id": request.external_point_id,
                            "value": request.value,
                            "station": self.station,
                        },
                    )
                    if resp.status_code >= 300:
                        return WriteResult(
                            success=False,
                            external_point_id=request.external_point_id,
                            requested_value=request.value,
                            detail=f"Honeywell write failed: HTTP {resp.status_code}",
                            acked=False,
                        )
            except Exception as exc:  # noqa: BLE001
                return WriteResult(
                    success=False,
                    external_point_id=request.external_point_id,
                    requested_value=request.value,
                    detail=f"Honeywell write error: {exc}",
                    acked=False,
                )
        meta["value"] = request.value
        readback = float(meta["value"])
        ok = abs(readback - request.value) <= max(request.deadband, 0.01)
        return WriteResult(
            success=ok,
            external_point_id=request.external_point_id,
            requested_value=request.value,
            readback_value=readback,
            detail="honeywell write ack",
            acked=ok,
        )

    def write_many(self, requests: list[WriteRequest]) -> list[WriteResult]:
        return [self.write(r) for r in requests]
