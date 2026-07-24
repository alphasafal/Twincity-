"""Static catalog of TwinPilot MCP resources and tools.

This module is the single source of truth used by both the official SDK
server and the stdio JSON-RPC fallback.
"""

from __future__ import annotations

from typing import Any

# Explicitly forbidden — never expose unrestricted actuation.
FORBIDDEN_TOOLS = frozenset({"set_any_actuator"})

RESOURCES: list[dict[str, str]] = [
    {
        "uri": "building://metadata",
        "name": "Building metadata",
        "description": "Static building identity, location, type, and area.",
        "mimeType": "application/json",
    },
    {
        "uri": "building://current-state",
        "name": "Current building state",
        "description": "Live operating mode, KPIs, telemetry snapshot, and confidence.",
        "mimeType": "application/json",
    },
    {
        "uri": "building://zones",
        "name": "Zones",
        "description": "Zone inventory with preferred and allowed temperature bands.",
        "mimeType": "application/json",
    },
    {
        "uri": "building://constraints",
        "name": "Constraint policy",
        "description": "Hard control limits enforced by the Safety Shield.",
        "mimeType": "application/json",
    },
    {
        "uri": "building://comfort-policy",
        "name": "Comfort policy",
        "description": "Comfort bands composed from zones and constraints.",
        "mimeType": "application/json",
    },
    {
        "uri": "building://goals",
        "name": "Goal profile",
        "description": "Active multi-objective optimization weights.",
        "mimeType": "application/json",
    },
    {
        "uri": "building://weather-forecast",
        "name": "Weather forecast",
        "description": "Simulated outdoor weather / tariff / carbon forecast.",
        "mimeType": "application/json",
    },
    {
        "uri": "building://occupancy-forecast",
        "name": "Occupancy forecast",
        "description": "Simulated zone occupancy forecast.",
        "mimeType": "application/json",
    },
    {
        "uri": "building://active-alerts",
        "name": "Active alerts",
        "description": "Unresolved building alerts.",
        "mimeType": "application/json",
    },
    {
        "uri": "building://decision-history",
        "name": "Decision history",
        "description": "Recent control decisions and outcomes.",
        "mimeType": "application/json",
    },
    {
        "uri": "building://service-health",
        "name": "Service health",
        "description": "API /health and /ready status.",
        "mimeType": "application/json",
    },
]

TOOLS: list[dict[str, Any]] = [
    {
        "name": "get_building_state",
        "description": "Fetch the current building status, mode, KPIs, and live state.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_zone_state",
        "description": "Fetch metadata and live health for a single zone.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "zone_id": {"type": "string", "description": "Zone UUID"},
            },
            "required": ["zone_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_active_alerts",
        "description": "List unresolved building alerts.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "get_forecast",
        "description": "Return weather and/or occupancy forecasts (simulated).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "forecast_type": {
                    "type": "string",
                    "enum": ["weather", "occupancy", "both"],
                    "default": "both",
                },
                "horizon_steps": {"type": "integer", "default": 16, "minimum": 1, "maximum": 96},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "get_baseline_kpis",
        "description": "Return baseline vs TwinPilot KPI summary (simulated).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "generate_candidate_plans",
        "description": "Generate optimization candidate plans for the building.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "energy_weight": {"type": "number", "default": 0.25},
                "cost_weight": {"type": "number", "default": 0.20},
                "carbon_weight": {"type": "number", "default": 0.20},
                "comfort_weight": {"type": "number", "default": 0.20},
                "peak_weight": {"type": "number", "default": 0.10},
                "equipment_weight": {"type": "number", "default": 0.05},
                "energy_target_pct": {"type": "number"},
                "zero_comfort_deviation": {"type": "boolean", "default": False},
                "allow_schedule_changes": {"type": "boolean", "default": True},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "simulate_plan",
        "description": "Simulate a candidate control plan before validation.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string"},
            },
            "required": ["plan_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "validate_plan",
        "description": "Run Safety Shield validation and obtain a validation_token.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string"},
            },
            "required": ["plan_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "request_plan_approval",
        "description": "Request operator/manager approval for a validated plan.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_id": {"type": "string"},
                "reason": {"type": "string", "minLength": 3},
            },
            "required": ["plan_id", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "apply_validated_plan",
        "description": (
            "Apply a plan that already passed Safety Shield validation. "
            "Requires validation_token from validate_plan."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "validation_token": {
                    "type": "string",
                    "description": "Token returned by validate_plan / Safety Shield",
                },
                "plan_id": {
                    "type": "string",
                    "description": "Optional plan id; inferred from token when omitted",
                },
            },
            "required": ["validation_token"],
            "additionalProperties": False,
        },
    },
    {
        "name": "request_zone_setpoint",
        "description": (
            "Request a temporary zone cooling setpoint override through the Safety Shield. "
            "Requires zone_id, temperature, duration, and reason."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "zone_id": {"type": "string"},
                "temperature": {"type": "number", "description": "Requested cooling setpoint °C"},
                "duration": {
                    "type": "integer",
                    "description": "Duration in minutes",
                    "minimum": 5,
                    "maximum": 240,
                },
                "reason": {"type": "string", "minLength": 3},
            },
            "required": ["zone_id", "temperature", "duration", "reason"],
            "additionalProperties": False,
        },
    },
    {
        "name": "rollback_to_safe_policy",
        "description": "Roll the building back to the default safe setpoint policy.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "default": "MCP rollback to safe policy"},
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "explain_decision",
        "description": "Explain why a past decision was made (agent-backed).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "decision_id": {"type": "string"},
            },
            "required": ["decision_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "get_analytics_summary",
        "description": "Return analytics summary for the building (simulated savings).",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]

TOOL_NAMES = frozenset(t["name"] for t in TOOLS)
RESOURCE_URIS = frozenset(r["uri"] for r in RESOURCES)

assert FORBIDDEN_TOOLS.isdisjoint(TOOL_NAMES), "Forbidden tools must never be registered"
