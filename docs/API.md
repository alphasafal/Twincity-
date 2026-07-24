# TwinPilot API

Base URL (local): `http://localhost:8000`  
OpenAPI: `http://localhost:8000/docs`  
Prefix: `/api/v1`

Auth: `Authorization: Bearer <access_token>` (JWT).  
WebSocket: `ws://localhost:8000/ws/buildings/{building_id}` (no auth in demo).

Responses that include live KPIs typically set `"simulated": true` when using the mock twin.

---

## Health

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | API + simulator + component health |
| GET | `/ready` | No | Building seeded + state primed |

---

## Auth

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/auth/login` | `{ email, password }` → access + refresh |
| POST | `/api/v1/auth/refresh` | `{ refresh_token }` |
| POST | `/api/v1/auth/logout` | Authenticated logout ack |
| GET | `/api/v1/auth/me` | Current user |

Demo users are documented in the root README (dev only).

---

## Buildings & modes

| Method | Path | Notes |
|--------|------|-------|
| GET | `/buildings` | List |
| GET | `/buildings/{id}` | Detail |
| GET | `/buildings/{id}/status` | Mode, KPIs, live state, service health |
| PATCH | `/buildings/{id}/mode` | Requires `mode_change` (Administrator) |
| POST | `/buildings/{id}/rollback` | Safe-policy rollback |
| GET | `/buildings/{id}/constraints` | Hard limits |
| GET | `/buildings/{id}/goals` | Active objective weights |

---

## Zones & telemetry

| Method | Path | Notes |
|--------|------|-------|
| GET | `/buildings/{id}/zones` | Zone list |
| GET | `/zones/{id}` | Zone detail |
| GET | `/zones/{id}/telemetry` | Recent points |
| GET | `/zones/{id}/health` | Live sensor/comfort |
| POST | `/zones/{id}/override` | Manual setpoint (`confirm: true`) |
| GET | `/buildings/{id}/telemetry/latest` | Hub state |
| GET | `/buildings/{id}/telemetry/history` | Metric history |
| POST | `/telemetry/ingest` | Batch ingest (`x-telemetry-token` when not demo) |

---

## Optimization & plans

| Method | Path | Notes |
|--------|------|-------|
| POST | `/buildings/{id}/optimization/generate` | Candidate plans + scores |
| GET | `/control-plans/{id}` | Plan detail |
| POST | `/control-plans/{id}/simulate` | Forward sim |
| POST | `/control-plans/{id}/validate` | Safety Shield → `validation_token` |
| POST | `/control-plans/{id}/approve` | RBAC by risk |
| POST | `/control-plans/{id}/reject` | Reject + audit |
| POST | `/control-plans/{id}/apply` | Re-validates then applies |

---

## Decisions, alerts, analytics, audit

| Method | Path |
|--------|------|
| GET | `/buildings/{id}/decisions` |
| GET | `/decisions/{id}` |
| GET | `/decisions/{id}/explanation` |
| GET | `/buildings/{id}/alerts` |
| PATCH | `/alerts/{id}/acknowledge` |
| PATCH | `/alerts/{id}/resolve` |
| POST | `/alerts/{id}/notes` |
| GET | `/buildings/{id}/analytics/summary` |
| GET | `/buildings/{id}/analytics/timeseries` |
| GET | `/buildings/{id}/analytics/export` |
| GET | `/buildings/{id}/ledger` |
| GET | `/buildings/{id}/audit` |
| POST | `/buildings/{id}/what-if` |

Analytics payloads are labeled **simulated** for the mock twin.

---

## Demo controls

| Method | Path |
|--------|------|
| GET | `/demo/scenarios` |
| POST | `/demo/scenarios/{id}/start` |
| POST | `/demo/scenarios/reset` |
| POST | `/demo/speed` |
| POST | `/demo/playback/{pause\|resume\|step\|reset}` |

Scenarios: `normal_hot_day`, `occupancy_spike`, `carbon_intensive`, `faulty_sensor`, `infeasible_target`, `simulation_failure`, `rollback`.

---

## Assistant

| Method | Path |
|--------|------|
| POST | `/assistant/chat` |
| GET | `/assistant/conversations` |
| GET | `/assistant/conversations/{id}` |

Uses `AGENT_PROVIDER` (`deterministic` or `ollama`).

---

## Users

| Method | Path | Notes |
|--------|------|-------|
| GET | `/users` | Administrator only |

---

## WebSocket events

Envelope:

```json
{
  "event_type": "telemetry.updated",
  "event_id": "uuid",
  "building_id": "uuid",
  "timestamp": "...",
  "payload": {},
  "schema_version": "1.0"
}
```

Emitted types (runtime):

| `event_type` | Meaning |
|--------------|---------|
| `telemetry.updated` | Twin state refresh |
| `building.mode_changed` | Mode / confidence |
| `decision.created` | New decision |
| `control.applied` | Action applied |
| `control.rejected` | Shield rejected |
| `alert.created` | Alert / loop error |
| `rollback.started` / `rollback.completed` | Rollback lifecycle |

Web clients may also synthesize `telemetry.poll` when WS is unavailable.

---

## RBAC (summary)

| Permission | Roles |
|------------|-------|
| `mode_change` | Administrator |
| `plan_approve_low` | Admin, Manager, Operator |
| `plan_approve_high` / high-risk approve | Admin, Manager |
| `plan_execute` | Admin, Manager |
| `manual_override` / `rollback` | Admin, Manager, Operator |
| `simulation_run` | Admin, Manager |
| `user_manage` | Administrator |
