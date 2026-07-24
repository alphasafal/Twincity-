# TwinPilot MCP

TwinPilot exposes a Model Context Protocol (MCP) server so LLM agents can read building context and propose **guarded** control actions. The server lives at `services/mcp-server` (package `twinpilot-mcp`) and talks to the TwinPilot REST API.

## Design principles

1. **Resources are read-only** — they load context into the model; they never actuate.
2. **Tools are narrowly scoped** — each tool maps to a specific TwinPilot API capability.
3. **Safety Shield is mandatory** — plans must be validated (and often approved) before apply.
4. **No unrestricted actuation** — `set_any_actuator` is forbidden and never registered.

## Running the server

```bash
cd services/mcp-server
pip install -e .
export TWINPILOT_API_URL=http://localhost:8000
python -m twinpilot_mcp
```

See `services/mcp-server/README.md` for environment variables and host configuration.

Default auth uses demo facility-manager credentials against `TWINPILOT_API_URL` (service/demo auth). Override with `TWINPILOT_API_EMAIL` / `TWINPILOT_API_PASSWORD` or `TWINPILOT_API_TOKEN`.

---

## Resources (read-only)

| URI | Description | API backing |
|-----|-------------|-------------|
| `building://metadata` | Building identity, location, type, area | `GET /api/v1/buildings/{id}` |
| `building://current-state` | Mode, KPIs, live telemetry, confidence | `GET /api/v1/buildings/{id}/status` |
| `building://zones` | Zone inventory and temperature bands | `GET /api/v1/buildings/{id}/zones` |
| `building://constraints` | Hard control limits | `GET /api/v1/buildings/{id}/constraints` |
| `building://comfort-policy` | Comfort bands (composed) | Composed from zones + constraints |
| `building://goals` | Active objective weights | `GET /api/v1/buildings/{id}/goals` |
| `building://weather-forecast` | Outdoor / tariff / carbon forecast | Derived from live state (simulated) |
| `building://occupancy-forecast` | Zone occupancy forecast | Derived from live state (simulated) |
| `building://active-alerts` | Unresolved alerts | `GET /api/v1/buildings/{id}/alerts` |
| `building://decision-history` | Recent decisions | `GET /api/v1/buildings/{id}/decisions` |
| `building://service-health` | Health / readiness | `GET /health`, `GET /ready` |

All resources return JSON (`application/json`).

---

## Tools

| Tool | Purpose | Required args | API backing |
|------|---------|---------------|-------------|
| `get_building_state` | Current status + live state | — | `GET .../status` |
| `get_zone_state` | Zone metadata + health | `zone_id` | `GET /zones/{id}`, `.../health` |
| `get_active_alerts` | Unresolved alerts | — | `GET .../alerts` |
| `get_forecast` | Weather and/or occupancy forecast | optional `forecast_type`, `horizon_steps` | Derived (simulated) |
| `get_baseline_kpis` | Baseline vs TwinPilot KPIs | — | analytics summary + status |
| `generate_candidate_plans` | Create optimization candidates | optional weights / targets | `POST .../optimization/generate` |
| `simulate_plan` | Forward-simulate a plan | `plan_id` | `POST /control-plans/{id}/simulate` |
| `validate_plan` | Safety Shield validation → `validation_token` | `plan_id` | `POST /control-plans/{id}/validate` |
| `request_plan_approval` | Operator/manager approval | `plan_id`, `reason` | `POST /control-plans/{id}/approve` |
| `apply_validated_plan` | Apply after validation | **`validation_token`** (optional `plan_id`) | verifies token, then `POST .../apply` |
| `request_zone_setpoint` | Temporary zone setpoint | **`zone_id`**, **`temperature`**, **`duration`**, **`reason`** | `POST /zones/{id}/override` |
| `rollback_to_safe_policy` | Restore safe setpoints | optional `reason` | `POST .../rollback` |
| `explain_decision` | Natural-language decision explanation | `decision_id` | `GET /decisions/{id}/explanation` |
| `get_analytics_summary` | Savings / compliance summary | — | `GET .../analytics/summary` |

### Required argument details

#### `apply_validated_plan`

```json
{
  "validation_token": "v1:<plan_id>:<state_hash>:<issuer>:<ts>",
  "plan_id": "<optional if encoded in token>"
}
```

The MCP server refuses to call apply unless the supplied `validation_token` matches the plan's stored Safety Shield token.

#### `request_zone_setpoint`

```json
{
  "zone_id": "<uuid>",
  "temperature": 24.5,
  "duration": 60,
  "reason": "Occupant comfort request during meeting"
}
```

- `temperature` — requested cooling setpoint (°C)
- `duration` — minutes (API enforces 5–240)
- `reason` — audit trail (required)

---

## Safety rules

1. **Never register `set_any_actuator`.** Arbitrary actuator writes are out of scope for MCP.
2. **Validate before apply.** Agents must call `validate_plan` and use the returned `validation_token` with `apply_validated_plan`.
3. **Respect mode and RBAC.** Advisory/manual modes require approval; the API enforces role permissions (demo manager/admin for apply/override).
4. **Zone setpoints need justification.** `request_zone_setpoint` always requires `zone_id`, `temperature`, `duration`, and `reason`.
5. **Prefer rollback on risk.** Use `rollback_to_safe_policy` when sensors fail, confidence drops, or comfort risk is elevated.
6. **Treat forecasts and savings as simulated** unless explicitly labeled otherwise by the API.
7. **Do not bypass the Safety Shield.** MCP tools call the REST API; they do not talk to simulators or actuators directly.

### Forbidden

| Name | Status |
|------|--------|
| `set_any_actuator` | Forbidden — not implemented, not advertised |

### Recommended agent loop

```
get_building_state → get_forecast → generate_candidate_plans
  → simulate_plan → validate_plan → [request_plan_approval]
  → apply_validated_plan(validation_token=...)
```

On failure or elevated risk: `rollback_to_safe_policy` and `explain_decision`.

---

## Implementation notes

- Package: `twinpilot-mcp` (`services/mcp-server`)
- Entrypoint: `python -m twinpilot_mcp`
- Prefers official `mcp` FastMCP; falls back to low-level SDK, then a stdio JSON-RPC server that still documents the same catalog (`python -m twinpilot_mcp --catalog` / `--fallback`).
- Shared catalog: `twinpilot_mcp/catalog.py`
- Shared dispatch: `twinpilot_mcp/handlers.py`
- REST client: `twinpilot_mcp/client.py`
