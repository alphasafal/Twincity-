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

## Acceptance criteria (hackathon demo)

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Web login | ✅ |
| 2 | Mobile login | ✅ |
| 3 | Five live zones | ✅ |
| 4 | Real-time telemetry | ✅ (WS + poll fallback) |
| 5 | Seeded scenarios startable | ✅ |
| 6 | Multiple candidate plans | ✅ |
| 7 | Predicted energy/cost/carbon/peak/comfort | ✅ |
| 8 | Plan simulation | ✅ |
| 9 | Safety Shield approve/reject | ✅ |
| 10 | Validated plan apply | ✅ |
| 11 | Expired/stale plan rejection | ✅ |
| 12 | Decision + audit on apply | ✅ |
| 13 | Baseline vs TwinPilot dashboard | ✅ |
| 14 | Sensor fault → Guarded Mode | ✅ |
| 15 | Simulation failure blocks autonomy | ✅ |
| 16 | Infeasible target → max feasible | ✅ |
| 17 | Mobile critical alerts | ✅ (local/demo notifications) |
| 18 | Advisory plan approval | ✅ |
| 19 | Authorized rollback | ✅ |
| 20 | Prediction ledger updates | ✅ |
| 21 | Assistant explains decisions | ✅ (deterministic agent) |
| 22 | Works without LLM | ✅ |
| 23 | Works with mock simulator | ✅ |
| 24 | Docker Compose demo profile | ✅ |
| 25 | Critical safety tests pass | ✅ (`pytest` 18+) |
| 26 | README clean-checkout path | ✅ (`make setup` / `make demo`) |

### Latest hardening

| Item | Status |
|------|--------|
| Constraint / building / goals PATCH APIs | ✅ |
| User invite + activate/deactivate APIs | ✅ |
| Settings UI wired to write APIs | ✅ |
| Auth + assistant rate limiting | ✅ |
| `make replay` end-to-end walkthrough | ✅ |
| Optional `make ollama` (llama3.2:1b pulled in env) | ✅ (falls back if JSON invalid) |
| Playwright critical flows expanded | ✅ (local run; not required in CI) |

## Phase 8 — Production platform (1C + 2C)

| Criterion | Status | Notes |
|-----------|--------|-------|
| Multi-tenant orgs / memberships / invites | ✅ | `Organization`, `Membership`, `Invitation` |
| Org-scoped building access + authenticated WS | ✅ | |
| Stripe subscriptions + entitlements | ✅ | Mock checkout when Stripe unset |
| Postgres + Redis production Compose profile | ✅ | `docker compose --profile production` |
| API vs worker control-loop split | ✅ | `python -m app.worker` + Redis lease |
| Connector framework + PointMapping | ✅ | `services/connectors` |
| BACnet/IP + Modbus TCP read/write adapters | ✅ | Simulated transport + live probe |
| Honeywell Niagara certified adapter | ✅ | Sandbox + live REST path |
| HMAC validation tokens + write-ack | ✅ | `v2` tokens; FALLBACK on failure |
| Onboarding wizard + M&V ROI + compliance docs | ✅ | Settings UI + `docs/COMPLIANCE.md` |

## Acceptance summary

The repository meets the **demo acceptance bar** and ships a **production platform foundation**: multi-tenant SaaS, billing entitlements, vendor-agnostic connectors (BACnet/Modbus/Honeywell), HMAC safety tokens, write acknowledgements, and site certification gates. Live BMS certification per customer site remains an operational process (see `docs/HONEYWELL_CERTIFICATION.md`).

