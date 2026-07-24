# TwinPilot Build Status

Checklist of phases and acceptance criteria against the current repository.  
Legend: ✅ done · ⚠️ partial / simulated · ❌ not in scope for this demo

---

## Phase 0 — Repository & tooling

| Criterion | Status | Notes |
|-----------|--------|-------|
| Monorepo (apps, services, packages) | ✅ | pnpm + Python services |
| Root README + docs | ✅ | This pass |
| `.env.example`, Makefile, Compose | ✅ | demo / full / energyplus |
| CI lint/test | ✅ | `.github/workflows/ci.yml` |
| Shared packages stubs | ✅ | contracts, api-client, config, tokens, eslint-config |

---

## Phase 1 — Backend API & domain

| Criterion | Status | Notes |
|-----------|--------|-------|
| FastAPI app + health/ready | ✅ | `services/api` |
| JWT auth + RBAC | ✅ | Four demo roles |
| Buildings, zones, telemetry | ✅ | Seeded demo office |
| Plans / decisions / alerts / ledger / audit | ✅ | |
| WebSocket fan-out | ✅ | In-process hub |
| SQLite create_all + seed | ✅ | Alembic scaffold present |
| Postgres-ready URL | ⚠️ | Works if `DATABASE_URL` set; Compose `full` |

---

## Phase 2 — Optimizer & Safety Shield

| Criterion | Status | Notes |
|-----------|--------|-------|
| Multi-objective planner | ✅ | `twinpilot_optimizer` |
| Operating mode state machine | ✅ | Deterministic |
| Independent Safety Shield | ✅ | Unit tests |
| Validation tokens | ✅ | |
| Anomaly / confidence helpers | ✅ | Used by runtime |

---

## Phase 3 — Simulator

| Criterion | Status | Notes |
|-----------|--------|-------|
| Mock building twin | ✅ | Default |
| Demo scenarios + playback | ✅ | `/api/v1/demo/*` |
| EnergyPlus adapter | ⚠️ | Optional; falls back to mock |
| Sample IDF/EPW shipped | ⚠️ | Placeholders + README only |
| Real BMS / Honeywell | ❌ | Not in repo — do not invent |

---

## Phase 4 — Agent & MCP

| Criterion | Status | Notes |
|-----------|--------|-------|
| Deterministic agent | ✅ | Default |
| Ollama provider | ⚠️ | Optional runtime |
| MCP resources + guarded tools | ✅ | `services/mcp-server` |
| No unrestricted actuation tool | ✅ | Documented |

---

## Phase 5 — Web console

| Criterion | Status | Notes |
|-----------|--------|-------|
| Login + role-aware shell | ✅ | `apps/web` |
| Dashboard / zones / decisions / alerts | ✅ | |
| Optimization / digital twin / analytics | ✅ | |
| Simulator controls / assistant / audit / settings | ✅ | |
| Live WS with poll fallback | ✅ | |

---

## Phase 6 — Mobile

| Criterion | Status | Notes |
|-----------|--------|-------|
| Expo app structure | ✅ | `apps/mobile` |
| Approvals / alerts / rollback / offline banner | ✅ | |
| Store submission | ❌ | Demo only |

---

## Phase 7 — Demo readiness

| Criterion | Status | Notes |
|-----------|--------|-------|
| `make setup` / `make demo` | ✅ | Scripts |
| Documented demo credentials | ✅ | Dev only |
| 7-minute demo script | ✅ | [DEMO_SCRIPT.md](DEMO_SCRIPT.md) |
| Honest simulated labeling | ✅ | API + UI |
| Production certification | ❌ | Explicit non-goal |

---

## Acceptance summary

The repository meets the **demo acceptance bar**: end-to-end simulated autonomous optimization with verifiable safety gates, operator UIs, MCP, and optional EnergyPlus/Ollama. It does **not** meet a production BMS deployment bar.
