"""TwinPilot MCP server entrypoint.

Prefers the official `mcp` SDK FastMCP API. If that import/API shape is
unavailable, falls back to a stdio JSON-RPC server that still documents and
dispatches the same tools and resources.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any

from twinpilot_mcp.catalog import RESOURCES, TOOLS
from twinpilot_mcp.client import TwinPilotClient
from twinpilot_mcp.handlers import call_tool, read_resource

logger = logging.getLogger("twinpilot_mcp")

_CLIENT: TwinPilotClient | None = None


def get_client() -> TwinPilotClient:
    global _CLIENT
    if _CLIENT is None:
        _CLIENT = TwinPilotClient()
    return _CLIENT


def _tool_text(name: str, arguments: dict[str, Any] | None = None) -> str:
    return call_tool(get_client(), name, arguments)


def _resource_text(uri: str) -> str:
    return read_resource(get_client(), uri)


def build_fastmcp():
    """Build a FastMCP server when the official SDK is available."""
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP(
        "TwinPilot",
        instructions=(
            "TwinPilot MCP exposes read-only building resources and narrowly scoped "
            "control tools backed by the TwinPilot Safety Shield. "
            "Never invent a set_any_actuator tool. "
            "apply_validated_plan requires validation_token. "
            "request_zone_setpoint requires zone_id, temperature, duration, and reason."
        ),
    )

    @mcp.resource("building://metadata")
    def resource_metadata() -> str:
        return _resource_text("building://metadata")

    @mcp.resource("building://current-state")
    def resource_current_state() -> str:
        return _resource_text("building://current-state")

    @mcp.resource("building://zones")
    def resource_zones() -> str:
        return _resource_text("building://zones")

    @mcp.resource("building://constraints")
    def resource_constraints() -> str:
        return _resource_text("building://constraints")

    @mcp.resource("building://comfort-policy")
    def resource_comfort_policy() -> str:
        return _resource_text("building://comfort-policy")

    @mcp.resource("building://goals")
    def resource_goals() -> str:
        return _resource_text("building://goals")

    @mcp.resource("building://weather-forecast")
    def resource_weather_forecast() -> str:
        return _resource_text("building://weather-forecast")

    @mcp.resource("building://occupancy-forecast")
    def resource_occupancy_forecast() -> str:
        return _resource_text("building://occupancy-forecast")

    @mcp.resource("building://active-alerts")
    def resource_active_alerts() -> str:
        return _resource_text("building://active-alerts")

    @mcp.resource("building://decision-history")
    def resource_decision_history() -> str:
        return _resource_text("building://decision-history")

    @mcp.resource("building://service-health")
    def resource_service_health() -> str:
        return _resource_text("building://service-health")

    @mcp.tool()
    def get_building_state() -> str:
        """Fetch the current building status, mode, KPIs, and live state."""
        return _tool_text("get_building_state")

    @mcp.tool()
    def get_zone_state(zone_id: str) -> str:
        """Fetch metadata and live health for a single zone."""
        return _tool_text("get_zone_state", {"zone_id": zone_id})

    @mcp.tool()
    def get_active_alerts() -> str:
        """List unresolved building alerts."""
        return _tool_text("get_active_alerts")

    @mcp.tool()
    def get_forecast(forecast_type: str = "both", horizon_steps: int = 16) -> str:
        """Return weather and/or occupancy forecasts (simulated)."""
        return _tool_text(
            "get_forecast",
            {"forecast_type": forecast_type, "horizon_steps": horizon_steps},
        )

    @mcp.tool()
    def get_baseline_kpis() -> str:
        """Return baseline vs TwinPilot KPI summary (simulated)."""
        return _tool_text("get_baseline_kpis")

    @mcp.tool()
    def generate_candidate_plans(
        energy_weight: float = 0.25,
        cost_weight: float = 0.20,
        carbon_weight: float = 0.20,
        comfort_weight: float = 0.20,
        peak_weight: float = 0.10,
        equipment_weight: float = 0.05,
        energy_target_pct: float | None = None,
        zero_comfort_deviation: bool = False,
        allow_schedule_changes: bool = True,
    ) -> str:
        """Generate optimization candidate plans for the building."""
        return _tool_text(
            "generate_candidate_plans",
            {
                "energy_weight": energy_weight,
                "cost_weight": cost_weight,
                "carbon_weight": carbon_weight,
                "comfort_weight": comfort_weight,
                "peak_weight": peak_weight,
                "equipment_weight": equipment_weight,
                "energy_target_pct": energy_target_pct,
                "zero_comfort_deviation": zero_comfort_deviation,
                "allow_schedule_changes": allow_schedule_changes,
            },
        )

    @mcp.tool()
    def simulate_plan(plan_id: str) -> str:
        """Simulate a candidate control plan before validation."""
        return _tool_text("simulate_plan", {"plan_id": plan_id})

    @mcp.tool()
    def validate_plan(plan_id: str) -> str:
        """Run Safety Shield validation and obtain a validation_token."""
        return _tool_text("validate_plan", {"plan_id": plan_id})

    @mcp.tool()
    def request_plan_approval(plan_id: str, reason: str) -> str:
        """Request operator/manager approval for a validated plan."""
        return _tool_text("request_plan_approval", {"plan_id": plan_id, "reason": reason})

    @mcp.tool()
    def apply_validated_plan(validation_token: str, plan_id: str | None = None) -> str:
        """Apply a plan that already passed Safety Shield validation."""
        args: dict[str, Any] = {"validation_token": validation_token}
        if plan_id:
            args["plan_id"] = plan_id
        return _tool_text("apply_validated_plan", args)

    @mcp.tool()
    def request_zone_setpoint(
        zone_id: str,
        temperature: float,
        duration: int,
        reason: str,
    ) -> str:
        """Request a temporary zone cooling setpoint through the Safety Shield."""
        return _tool_text(
            "request_zone_setpoint",
            {
                "zone_id": zone_id,
                "temperature": temperature,
                "duration": duration,
                "reason": reason,
            },
        )

    @mcp.tool()
    def rollback_to_safe_policy(reason: str = "MCP rollback to safe policy") -> str:
        """Roll the building back to the default safe setpoint policy."""
        return _tool_text("rollback_to_safe_policy", {"reason": reason})

    @mcp.tool()
    def explain_decision(decision_id: str) -> str:
        """Explain why a past decision was made (agent-backed)."""
        return _tool_text("explain_decision", {"decision_id": decision_id})

    @mcp.tool()
    def get_analytics_summary() -> str:
        """Return analytics summary for the building (simulated savings)."""
        return _tool_text("get_analytics_summary")

    return mcp


def run_with_fastmcp() -> None:
    mcp = build_fastmcp()
    transport = os.getenv("TWINPILOT_MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        # Allow streamable-http / sse when the installed SDK supports them.
        mcp.run(transport=transport)


def run_with_low_level_sdk() -> None:
    """Alternate official-SDK path using Server + stdio_server."""
    import anyio
    from mcp.server import NotificationOptions, Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Resource,
        TextContent,
        Tool,
    )

    server = Server("twinpilot-mcp")

    @server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri=r["uri"],
                name=r["name"],
                description=r.get("description"),
                mimeType=r.get("mimeType", "application/json"),
            )
            for r in RESOURCES
        ]

    @server.read_resource()
    async def read_resource_handler(uri: str):  # type: ignore[no-untyped-def]
        text = _resource_text(str(uri))
        return text

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=t["name"],
                description=t.get("description"),
                inputSchema=t.get("inputSchema") or {"type": "object", "properties": {}},
            )
            for t in TOOLS
        ]

    @server.call_tool()
    async def call_tool_handler(name: str, arguments: dict[str, Any] | None):  # type: ignore[no-untyped-def]
        text = _tool_text(name, arguments or {})
        return [TextContent(type="text", text=text)]

    async def _main() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="twinpilot-mcp",
                    server_version="0.1.0",
                    capabilities=server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

    anyio.run(_main)


def dump_catalog() -> None:
    """Print tools/resources as JSON (useful for inspection without MCP host)."""
    print(
        json.dumps(
            {
                "server": "twinpilot-mcp",
                "api_url": os.getenv("TWINPILOT_API_URL", "http://localhost:8000"),
                "resources": RESOURCES,
                "tools": TOOLS,
                "safety": {
                    "forbidden_tools": ["set_any_actuator"],
                    "apply_validated_plan_requires": ["validation_token"],
                    "request_zone_setpoint_requires": [
                        "zone_id",
                        "temperature",
                        "duration",
                        "reason",
                    ],
                },
            },
            indent=2,
        )
    )


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    # Stdout is reserved for MCP protocol when running a server; log to stderr.
    logging.basicConfig(
        level=os.getenv("TWINPILOT_MCP_LOG", "INFO"),
        stream=sys.stderr,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if "--catalog" in args:
        dump_catalog()
        return

    mode = os.getenv("TWINPILOT_MCP_MODE", "").strip().lower()
    if mode == "energyplus_experiment" or "--energyplus-experiment" in args:
        from twinpilot_mcp.energyplus_experiment_server import run_energyplus_experiment_stdio

        run_energyplus_experiment_stdio()
        return

    force_fallback = "--fallback" in args or os.getenv("TWINPILOT_MCP_FORCE_FALLBACK") == "1"
    if force_fallback:
        logger.info("Starting TwinPilot MCP stdio JSON-RPC fallback server")
        from twinpilot_mcp.fallback import run_fallback

        run_fallback()
        return

    # Prefer FastMCP, then low-level SDK, then stdio fallback.
    try:
        logger.info("Starting TwinPilot MCP via FastMCP (official mcp SDK)")
        run_with_fastmcp()
        return
    except Exception as fastmcp_exc:  # noqa: BLE001
        logger.warning("FastMCP unavailable or failed (%s); trying low-level SDK", fastmcp_exc)

    try:
        logger.info("Starting TwinPilot MCP via low-level mcp.server.Server")
        run_with_low_level_sdk()
        return
    except Exception as low_exc:  # noqa: BLE001
        logger.warning("Low-level MCP SDK unavailable or failed (%s); using fallback", low_exc)

    logger.info("Starting TwinPilot MCP stdio JSON-RPC fallback server")
    from twinpilot_mcp.fallback import run_fallback

    run_fallback()


if __name__ == "__main__":
    main()
