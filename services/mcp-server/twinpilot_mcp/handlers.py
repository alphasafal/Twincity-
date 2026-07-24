"""Shared resource/tool dispatch used by FastMCP and fallback servers."""

from __future__ import annotations

import json
from typing import Any

from twinpilot_mcp.catalog import FORBIDDEN_TOOLS, RESOURCE_URIS, TOOL_NAMES
from twinpilot_mcp.client import TwinPilotClient


def _json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def read_resource(client: TwinPilotClient, uri: str) -> str:
    if uri not in RESOURCE_URIS:
        raise ValueError(f"Unknown resource URI: {uri}")
    mapping = {
        "building://metadata": client.building_metadata,
        "building://current-state": client.current_state,
        "building://zones": client.zones,
        "building://constraints": client.constraints,
        "building://comfort-policy": client.comfort_policy,
        "building://goals": client.goals,
        "building://weather-forecast": client.weather_forecast,
        "building://occupancy-forecast": client.occupancy_forecast,
        "building://active-alerts": client.active_alerts,
        "building://decision-history": client.decision_history,
        "building://service-health": client.service_health,
    }
    return _json(mapping[uri]())


def call_tool(client: TwinPilotClient, name: str, arguments: dict[str, Any] | None = None) -> str:
    if name in FORBIDDEN_TOOLS:
        raise PermissionError(
            f"Tool '{name}' is forbidden. TwinPilot MCP never exposes unrestricted actuation."
        )
    if name not in TOOL_NAMES:
        raise ValueError(f"Unknown tool: {name}")

    args = arguments or {}

    if name == "get_building_state":
        result = client.get_building_state()
    elif name == "get_zone_state":
        result = client.get_zone_state(str(args["zone_id"]))
    elif name == "get_active_alerts":
        result = client.get_active_alerts()
    elif name == "get_forecast":
        result = client.get_forecast(
            forecast_type=str(args.get("forecast_type", "both")),
            horizon_steps=int(args.get("horizon_steps", 16)),
        )
    elif name == "get_baseline_kpis":
        result = client.get_baseline_kpis()
    elif name == "generate_candidate_plans":
        result = client.generate_candidate_plans(
            energy_weight=float(args.get("energy_weight", 0.25)),
            cost_weight=float(args.get("cost_weight", 0.20)),
            carbon_weight=float(args.get("carbon_weight", 0.20)),
            comfort_weight=float(args.get("comfort_weight", 0.20)),
            peak_weight=float(args.get("peak_weight", 0.10)),
            equipment_weight=float(args.get("equipment_weight", 0.05)),
            energy_target_pct=(
                float(args["energy_target_pct"]) if args.get("energy_target_pct") is not None else None
            ),
            zero_comfort_deviation=bool(args.get("zero_comfort_deviation", False)),
            allow_schedule_changes=bool(args.get("allow_schedule_changes", True)),
        )
    elif name == "simulate_plan":
        result = client.simulate_plan(str(args["plan_id"]))
    elif name == "validate_plan":
        result = client.validate_plan(str(args["plan_id"]))
    elif name == "request_plan_approval":
        result = client.request_plan_approval(str(args["plan_id"]), str(args["reason"]))
    elif name == "apply_validated_plan":
        result = client.apply_validated_plan(
            validation_token=str(args["validation_token"]),
            plan_id=str(args["plan_id"]) if args.get("plan_id") else None,
        )
    elif name == "request_zone_setpoint":
        result = client.request_zone_setpoint(
            zone_id=str(args["zone_id"]),
            temperature=float(args["temperature"]),
            duration=int(args["duration"]),
            reason=str(args["reason"]),
        )
    elif name == "rollback_to_safe_policy":
        result = client.rollback_to_safe_policy(
            reason=str(args.get("reason", "MCP rollback to safe policy"))
        )
    elif name == "explain_decision":
        result = client.explain_decision(str(args["decision_id"]))
    elif name == "get_analytics_summary":
        result = client.get_analytics_summary()
    else:  # pragma: no cover - guarded by TOOL_NAMES
        raise ValueError(f"Unhandled tool: {name}")

    return _json(result)
