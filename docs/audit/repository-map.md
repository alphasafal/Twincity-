# Repository Map — TwinPilot / Eco-Loop Building Agents

**Audit date:** 2026-07-25  
**Branch audited:** `cursor/ecoloop-energyplus-audit-b6b3` (from `cursor/twinpilot-platform-b6b3`)  
**Product name in repo:** TwinPilot (concept: Eco-Loop Building Agents)

This document is an evidence-based map. Claims of “working” require executable proof elsewhere in `docs/audit/`.

---

## 1. Architecture map

```text
┌─────────────┐   ┌──────────────┐   ┌─────────────────┐
│ apps/web    │   │ apps/mobile  │   │ MCP server      │
│ Next.js 15  │   │ Expo 52      │   │ twinpilot_mcp   │
└──────┬──────┘   └──────┬───────┘   └────────┬────────┘
       │ REST/WS         │ REST               │ REST
       └─────────────────┼────────────────────┘
                         ▼
              ┌──────────────────────┐
              │ services/api FastAPI │
              │ RuntimeHub control   │
              │ loop (in-process)    │
              └──────────┬───────────┘
         ┌───────────────┼────────────────┐
         ▼               ▼                ▼
  optimizer pkg    simulator pkg     agent pkg
  SafetyShield     Mock (default)    Deterministic
  planner          EnergyPlusAdapter (default)
                   (was stub→mock)   Ollama optional
         │
         ▼
   SQLite / Postgres   AuditEvent Decision Alert Ledger
```

---

## 2. Application entry points

| Surface | Entry | Command |
|---------|-------|---------|
| API | `services/api/app/main.py` → `app` | `make api` / `uvicorn app.main:app` |
| Web | `apps/web` Next App Router | `make web` / `make demo` |
| Mobile | `apps/mobile` Expo Router | `make mobile` |
| MCP | `python -m twinpilot_mcp` | `services/mcp-server` |
| Control loop | `RuntimeHub` in `services/api/app/services/runtime.py` | started in API lifespan |
| Experiments | `scripts/run_baseline.sh`, `scripts/run_agent.sh` | Phase 3 harness |

---

## 3. Frontend stack

- **Web:** Next.js 15, React 19, TypeScript, Tailwind, TanStack Query, Zustand, Zod, Recharts, Playwright e2e scaffold
- **Mobile:** Expo 52, Expo Router, TanStack Query, Zustand, SecureStore, local notifications abstraction
- **Not present:** shadcn/ui / Radix (custom industrial components)

---

## 4. Backend stack

- FastAPI + Pydantic + SQLAlchemy + JWT (python-jose) + passlib/bcrypt
- SQLite default (`DATABASE_URL=sqlite:///./twinpilot.db`); Postgres via Compose `full`
- In-process WebSocket hub
- Alembic scaffold only (`create_all` at startup) — **no migration revisions**

---

## 5. EnergyPlus integration method (as found)

| Item | Finding |
|------|---------|
| Class | `EnergyPlusAdapter` in `services/simulator/twinpilot_simulator/energyplus.py` |
| Env | `SIMULATOR_PROVIDER`, `ENERGYPLUS_HOME`, `ENERGYPLUS_MODEL_PATH`, `ENERGYPLUS_WEATHER_PATH` |
| IDF/EPW in repo (pre-audit) | **None** — only README placeholders under `building-models/` |
| Live process | **Not implemented** — adapter imported `pyenergyplus.api` optionally then delegated all dynamics to `MockBuildingSimulator` |
| Control injection | `apply_action` → mock only |
| Status label | API `building_status` hardcoded `"simulated": True` |

**Classification:** P0 — blocks a real EnergyPlus closed-loop claim.

---

## 6. MCP server and tools

- Package: `services/mcp-server/twinpilot_mcp`
- Resources: `building://metadata|current-state|zones|constraints|comfort-policy|goals|weather-forecast|occupancy-forecast|active-alerts|decision-history|service-health`
- Tools (14): `get_building_state`, `get_zone_state`, `get_active_alerts`, `get_forecast`, `get_baseline_kpis`, `generate_candidate_plans`, `simulate_plan`, `validate_plan`, `request_plan_approval`, `apply_validated_plan`, `request_zone_setpoint`, `rollback_to_safe_policy`, `explain_decision`, `get_analytics_summary`
- Forbidden: `set_any_actuator`
- Implementation: HTTP client to TwinPilot API (real REST). Forecasts synthesized client-side when no forecast API exists.

---

## 7. LLM provider and agent orchestration

- `DeterministicAgentProvider` (default `AGENT_PROVIDER=deterministic`)
- `OllamaAgentProvider` (`AGENT_PROVIDER=ollama`, model e.g. `llama3.2:1b`)
- Used for `/api/v1/assistant/chat` and decision explanation — **not** for direct actuation
- Malformed LLM JSON → one repair → deterministic fallback + reasoning note
- Actuation only via Safety Shield–gated API/MCP apply paths

---

## 8. Database / persistence

Entities: User, Building, Zone, Sensor, TelemetryPoint, ComfortPolicy, GoalProfile, ConstraintPolicy, Forecast, ControlPlan, ControlAction, SimulationRun, Decision, Alert, AuditEvent, AssistantConversation, PredictionLedgerEntry

---

## 9. Simulation inputs/outputs (post-fix)

- Inputs: `building-models/sample-office/office_5zone.idf`, `building-models/weather/chicago.epw`
- Experiment outputs: `results/{baseline,agent}/summary.json`, `results/comparison/comparison.json`
- Mock path outputs: in-memory `BuildingState`, KPI history with synthetic baseline `power * 1.12` **only when `simulated=true`** (labeled)

---

## 10. Environment variables

See `.env.example`. Critical: `DEMO_MODE`, `SIMULATOR_PROVIDER`, `AGENT_PROVIDER`, `ENERGYPLUS_*`, `OLLAMA_*`, `JWT_*`, `DATABASE_URL`, `CONTROL_LOOP_ENABLED`.

---

## 11. Startup commands

```bash
make setup && make demo
make replay
docker compose --profile demo up --build
make energyplus-check
```

---

## 12. Test infrastructure

- Unit: `services/api/tests/test_safety.py`, `test_objective_modes.py`
- Integration: `tests/integration/test_control_flow.py`, `test_approve_apply_rollback.py`, `test_settings_and_rate_limit.py`
- Web: Playwright `apps/web/e2e`
- CI: `.github/workflows/ci.yml` (API ruff/pytest + web typecheck/lint)
- **Missing pre-audit:** EnergyPlus adapter tests, failure-mode suite for E+/MCP down, baseline/agent experiment automation

---

## 13. Mocked / placeholder components (inventory)

| Component | Status |
|-----------|--------|
| `MockBuildingSimulator` | Real mock twin (deterministic) |
| `EnergyPlusAdapter` (pre-fix) | Stub over mock |
| IDF/EPW assets | Placeholder READMEs only |
| Baseline energy (`* 1.12`) | Synthetic |
| Realized metrics after apply | Scaled predictions |
| MCP weather/occupancy forecast | Synthesized |
| Honeywell / BACnet / BMS | Not present |
| Alembic versions | Empty |
| OpenAPI-generated client | Thin manual package |

---

## 14. Dead / incomplete modules

- EnergyPlus Compose profile wires env but does not install EnergyPlus
- `energyplus-check.sh` exits 0 when unset (soft fail)
- Settings previously read-only (write APIs added later — present on branch)
- No `scripts/run_baseline.sh` / `run_agent.sh` prior to this audit

---

## 15. P0 list — resolution

| P0 | Status |
|----|--------|
| Real EnergyPlus experiment runner | **Fixed** — `ep_experiment.py` + scripts |
| IDF/EPW assets | **Fixed** — sample office + Chicago EPW |
| Control injection | **Fixed** — `Clg-SetP-Sch` schedule actuator |
| Silent mock fallback | **Fixed** — strict unless `ENERGYPLUS_ALLOW_MOCK_FALLBACK=1` |
| Dashboard hardcoded simulated | **Fixed** — state-driven + labels |

Remaining non-P0: live UI still mock-default; see `FINAL_HACKATHON_READINESS_REPORT.md`.
