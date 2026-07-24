"""HTTP client for the TwinPilot REST API."""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_EMAIL = "manager@twinpilot.demo"
DEFAULT_PASSWORD = "TwinPilot-Manager-Demo!"


class TwinPilotClient:
    """Authenticated TwinPilot API client used by MCP tools and resources."""

    def __init__(
        self,
        base_url: str | None = None,
        *,
        email: str | None = None,
        password: str | None = None,
        building_id: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = (base_url or os.getenv("TWINPILOT_API_URL", DEFAULT_API_URL)).rstrip("/")
        self.email = email or os.getenv("TWINPILOT_API_EMAIL", DEFAULT_EMAIL)
        self.password = password or os.getenv("TWINPILOT_API_PASSWORD", DEFAULT_PASSWORD)
        self._building_id = building_id or os.getenv("TWINPILOT_BUILDING_ID")
        self._token: str | None = os.getenv("TWINPILOT_API_TOKEN")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> TwinPilotClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _headers(self) -> dict[str, str]:
        self.ensure_auth()
        headers = {"Accept": "application/json"}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def ensure_auth(self) -> None:
        if self._token:
            return
        response = self._client.post(
            "/api/v1/auth/login",
            json={"email": self.email, "password": self.password},
        )
        response.raise_for_status()
        self._token = response.json()["access_token"]

    def request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        response = self._client.request(
            method,
            path,
            headers=self._headers(),
            json=json,
            params=params,
        )
        if response.status_code == 401 and not os.getenv("TWINPILOT_API_TOKEN"):
            self._token = None
            self.ensure_auth()
            response = self._client.request(
                method,
                path,
                headers=self._headers(),
                json=json,
                params=params,
            )
        response.raise_for_status()
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()

    def get(self, path: str, **kwargs: Any) -> Any:
        return self.request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Any:
        return self.request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Any:
        return self.request("PATCH", path, **kwargs)

    def resolve_building_id(self) -> str:
        if self._building_id:
            return self._building_id
        buildings = self.get("/api/v1/buildings")
        if not buildings:
            raise RuntimeError("No buildings available from TwinPilot API")
        self._building_id = buildings[0]["id"]
        return self._building_id

    # ── Resource helpers ───────────────────────────────────────────────

    def building_metadata(self) -> dict[str, Any]:
        building_id = self.resolve_building_id()
        return self.get(f"/api/v1/buildings/{building_id}")

    def current_state(self) -> dict[str, Any]:
        building_id = self.resolve_building_id()
        return self.get(f"/api/v1/buildings/{building_id}/status")

    def zones(self) -> list[dict[str, Any]]:
        building_id = self.resolve_building_id()
        return self.get(f"/api/v1/buildings/{building_id}/zones")

    def constraints(self) -> dict[str, Any]:
        building_id = self.resolve_building_id()
        return self.get(f"/api/v1/buildings/{building_id}/constraints")

    def comfort_policy(self) -> dict[str, Any]:
        """Compose comfort policy from zones + constraints (no dedicated REST route yet)."""
        zones = self.zones()
        constraints = self.constraints()
        return {
            "source": "composed",
            "building_id": self.resolve_building_id(),
            "occupied_band_c": {
                "min": min((z.get("minimum_temperature", 20) for z in zones), default=20),
                "max": max((z.get("maximum_temperature", 27) for z in zones), default=27),
            },
            "preferred_temperatures": {
                z["id"]: z.get("preferred_temperature") for z in zones
            },
            "setpoint_limits": {
                "min_cooling_setpoint": constraints.get("min_cooling_setpoint"),
                "max_cooling_setpoint": constraints.get("max_cooling_setpoint"),
                "min_heating_setpoint": constraints.get("min_heating_setpoint"),
                "max_heating_setpoint": constraints.get("max_heating_setpoint"),
                "max_setpoint_change_per_interval": constraints.get(
                    "max_setpoint_change_per_interval"
                ),
            },
            "label": "composed from zones and constraints",
        }

    def goals(self) -> dict[str, Any]:
        building_id = self.resolve_building_id()
        return self.get(f"/api/v1/buildings/{building_id}/goals")

    def weather_forecast(self, horizon_steps: int = 16) -> dict[str, Any]:
        status = self.current_state()
        state = status.get("state") or {}
        outdoor = float(state.get("outdoor_temperature", 32.0))
        humidity = float(state.get("outdoor_humidity", 55.0))
        carbon = float(state.get("grid_carbon_intensity", 700.0))
        tariff = float(state.get("electricity_tariff", 8.0))
        points = []
        for i in range(horizon_steps):
            # Simple diurnal-ish synthetic forecast from current live state
            drift = 1.5 * ((i % 8) - 4) / 4.0
            points.append(
                {
                    "step": i,
                    "outdoor_temperature_c": round(outdoor + drift, 2),
                    "outdoor_humidity_pct": round(humidity, 1),
                    "grid_carbon_intensity": round(carbon + (80 if 6 <= i <= 10 else 0), 1),
                    "electricity_tariff": round(tariff + (2.0 if 4 <= i <= 8 else 0.0), 2),
                }
            )
        return {
            "building_id": self.resolve_building_id(),
            "forecast_type": "weather",
            "horizon_steps": horizon_steps,
            "confidence": (status.get("confidence") or {}).get("forecast_confidence", 0.85),
            "points": points,
            "label": "simulated forecast derived from live state",
        }

    def occupancy_forecast(self, horizon_steps: int = 16) -> dict[str, Any]:
        status = self.current_state()
        state = status.get("state") or {}
        zones = state.get("zones") or {}
        points = []
        for i in range(horizon_steps):
            factor = 1.0 if i < 8 else 0.55
            zone_occ = {
                zid: max(0, int(z.get("occupancy_count", 0) * factor))
                for zid, z in zones.items()
            }
            points.append(
                {
                    "step": i,
                    "total_occupancy": sum(zone_occ.values()),
                    "zones": zone_occ,
                }
            )
        return {
            "building_id": self.resolve_building_id(),
            "forecast_type": "occupancy",
            "horizon_steps": horizon_steps,
            "confidence": (status.get("confidence") or {}).get("forecast_confidence", 0.85),
            "points": points,
            "label": "simulated forecast derived from live state",
        }

    def active_alerts(self) -> list[dict[str, Any]]:
        building_id = self.resolve_building_id()
        alerts = self.get(f"/api/v1/buildings/{building_id}/alerts")
        return [a for a in alerts if a.get("status") != "RESOLVED"]

    def decision_history(self) -> list[dict[str, Any]]:
        building_id = self.resolve_building_id()
        return self.get(f"/api/v1/buildings/{building_id}/decisions")

    def service_health(self) -> dict[str, Any]:
        health = self._client.get("/health").json()
        ready = self._client.get("/ready").json()
        return {"health": health, "ready": ready}

    # ── Tool helpers ───────────────────────────────────────────────────

    def get_building_state(self) -> dict[str, Any]:
        return self.current_state()

    def get_zone_state(self, zone_id: str) -> dict[str, Any]:
        zone = self.get(f"/api/v1/zones/{zone_id}")
        health = self.get(f"/api/v1/zones/{zone_id}/health")
        return {"zone": zone, "health": health}

    def get_active_alerts(self) -> list[dict[str, Any]]:
        return self.active_alerts()

    def get_forecast(self, forecast_type: str = "both", horizon_steps: int = 16) -> dict[str, Any]:
        out: dict[str, Any] = {"building_id": self.resolve_building_id()}
        if forecast_type in {"weather", "both"}:
            out["weather"] = self.weather_forecast(horizon_steps)
        if forecast_type in {"occupancy", "both"}:
            out["occupancy"] = self.occupancy_forecast(horizon_steps)
        return out

    def get_baseline_kpis(self) -> dict[str, Any]:
        building_id = self.resolve_building_id()
        summary = self.get(f"/api/v1/buildings/{building_id}/analytics/summary")
        status = self.current_state()
        return {
            "summary": summary,
            "baseline_energy_kwh": summary.get("baseline_energy_kwh"),
            "energy_saved_today_pct": status.get("energy_saved_today_pct"),
            "cost_saved_today": status.get("cost_saved_today"),
            "carbon_avoided_today_kg": status.get("carbon_avoided_today_kg"),
            "peak_demand_reduction_pct": status.get("peak_demand_reduction_pct"),
            "comfort_compliance_pct": status.get("comfort_compliance_pct"),
            "label": "simulated",
        }

    def generate_candidate_plans(
        self,
        *,
        energy_weight: float = 0.25,
        cost_weight: float = 0.20,
        carbon_weight: float = 0.20,
        comfort_weight: float = 0.20,
        peak_weight: float = 0.10,
        equipment_weight: float = 0.05,
        energy_target_pct: float | None = None,
        zero_comfort_deviation: bool = False,
        allow_schedule_changes: bool = True,
    ) -> dict[str, Any]:
        building_id = self.resolve_building_id()
        payload: dict[str, Any] = {
            "energy_weight": energy_weight,
            "cost_weight": cost_weight,
            "carbon_weight": carbon_weight,
            "comfort_weight": comfort_weight,
            "peak_weight": peak_weight,
            "equipment_weight": equipment_weight,
            "zero_comfort_deviation": zero_comfort_deviation,
            "allow_schedule_changes": allow_schedule_changes,
        }
        if energy_target_pct is not None:
            payload["energy_target_pct"] = energy_target_pct
        return self.post(f"/api/v1/buildings/{building_id}/optimization/generate", json=payload)

    def simulate_plan(self, plan_id: str) -> dict[str, Any]:
        return self.post(f"/api/v1/control-plans/{plan_id}/simulate")

    def validate_plan(self, plan_id: str) -> dict[str, Any]:
        return self.post(f"/api/v1/control-plans/{plan_id}/validate")

    def request_plan_approval(self, plan_id: str, reason: str) -> dict[str, Any]:
        return self.post(
            f"/api/v1/control-plans/{plan_id}/approve",
            json={"reason": reason},
        )

    def apply_validated_plan(self, validation_token: str, plan_id: str | None = None) -> dict[str, Any]:
        if not validation_token:
            raise ValueError("validation_token is required")
        if plan_id is None:
            # Token format: v1:{plan_id}:{state_hash}:{issuer}:{ts}
            parts = validation_token.split(":")
            if len(parts) < 2:
                raise ValueError("Invalid validation_token format")
            plan_id = parts[1]
        plan = self.get(f"/api/v1/control-plans/{plan_id}")
        stored = plan.get("validation_token")
        if not stored:
            raise ValueError("Plan has no validation_token; run validate_plan first")
        if stored != validation_token:
            raise ValueError("validation_token does not match the validated plan")
        return self.post(f"/api/v1/control-plans/{plan_id}/apply")

    def request_zone_setpoint(
        self,
        *,
        zone_id: str,
        temperature: float,
        duration: int,
        reason: str,
    ) -> dict[str, Any]:
        if not zone_id:
            raise ValueError("zone_id is required")
        if temperature is None:
            raise ValueError("temperature is required")
        if duration is None:
            raise ValueError("duration is required")
        if not reason:
            raise ValueError("reason is required")
        return self.post(
            f"/api/v1/zones/{zone_id}/override",
            json={
                "value": temperature,
                "duration_minutes": duration,
                "reason": reason,
                "confirm": True,
            },
        )

    def rollback_to_safe_policy(self, reason: str = "MCP rollback to safe policy") -> dict[str, Any]:
        building_id = self.resolve_building_id()
        return self.post(
            f"/api/v1/buildings/{building_id}/rollback",
            json={"reason": reason, "target_safe_policy": "default_safe_policy"},
        )

    def explain_decision(self, decision_id: str) -> dict[str, Any]:
        return self.get(f"/api/v1/decisions/{decision_id}/explanation")

    def get_analytics_summary(self) -> dict[str, Any]:
        building_id = self.resolve_building_id()
        return self.get(f"/api/v1/buildings/{building_id}/analytics/summary")
