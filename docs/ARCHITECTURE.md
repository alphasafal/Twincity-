# TwinPilot Architecture

TwinPilot separates **proposal** (optimizer / agent), **validation** (Safety Shield), and **actuation** (simulator apply / override). The API hosts an in-process control loop that steps the twin, generates plans, validates, and optionally applies them based on operating mode.

**Scope note:** This demo uses a **mock building simulator** by default. There is no production Honeywell/BMS integration in this repository.

---

## System overview

```mermaid
flowchart TB
  subgraph Clients
    W[Web Next.js]
    M[Mobile Expo]
    C[MCP / LLM host]
  end

  subgraph API["FastAPI services/api"]
    Auth[JWT Auth + RBAC]
    R[REST /api/v1]
    WS[WS /ws/buildings/id]
    RT[RuntimeHub control loop]
    SH[SafetyShield]
    AG[Agent provider]
  end

  OPT[twinpilot-optimizer]
  SIM[twinpilot-simulator]
  DB[(SQLAlchemy SQLite/Postgres)]

  W --> R
  W --> WS
  M --> R
  C --> R
  R --> Auth
  R --> RT
  R --> SH
  R --> AG
  RT --> OPT
  RT --> SIM
  RT --> SH
  R --> DB
  RT --> DB
  WS --> RT
```

---

## Control loop

```mermaid
sequenceDiagram
  participant Loop as Control loop
  participant Sim as Simulator
  participant Opt as Optimizer
  participant Shield as Safety Shield
  participant DB as Database
  participant WS as WebSocket clients

  loop every CONTROL_INTERVAL_SECONDS
    Loop->>Sim: step / get_state
    Loop->>Opt: generate_candidate_plans
    Loop->>Shield: validate selected action
    alt mode AUTONOMOUS/GUARDED and valid
      Loop->>Sim: apply_action
      Loop->>DB: Decision + ledger entry
    else ADVISORY / needs approval / invalid
      Loop->>DB: Decision PENDING or rejected
    end
    Loop->>WS: telemetry.updated / decision.created / ...
  end
```

Modes are managed by `twinpilot_optimizer.modes` (deterministic thresholds). Critical faults force **FALLBACK**; operators can force **MANUAL**.

---

## Safety architecture

```mermaid
flowchart LR
  Proposal[ProposedAction] --> Shield[SafetyShield.validate]
  Ctx[ValidationContext<br/>mode confidence sensors<br/>limits hash expiry] --> Shield
  Shield -->|valid + validation_token| Apply[apply / execute]
  Shield -->|invalid| Block[blocking_reasons]
  Apply --> Audit[AuditEvent + Decision]
```

Rules include setpoint ranges, max Δ per interval, duration caps, data freshness, sensor health, simulation OK, plan expiry, state-hash match, and mode-gated approval. See [SAFETY.md](SAFETY.md).

The Safety Shield lives in `services/optimizer` and is imported by the API — **not** by the LLM agent path for final authorization.

---

## MCP architecture

```mermaid
flowchart TB
  Host[MCP host Claude/Cursor] -->|stdio| Server[twinpilot-mcp]
  Server -->|resources read-only| API[TwinPilot REST]
  Server -->|tools narrow| API
  API --> Shield[Safety Shield]
  note1[No set_any_actuator tool]
```

Resources load context; mutating tools require validation tokens / RBAC-backed API calls. See [MCP.md](MCP.md).

---

## Deployment (demo)

```mermaid
flowchart LR
  Browser --> Web[:3000 Next.js]
  Browser --> API[:8000 FastAPI]
  Web --> API
  API --> DB[(SQLite volume)]
  API --> Twin[In-process mock twin]
```

Compose profiles:

| Profile | Services |
|---------|----------|
| `demo` | `api` + `web` (SQLite, no Redis) |
| `full` | `api` + `web` + optional `postgres` |
| `energyplus` | `api` + `web` with EnergyPlus env/mounts |

Details: [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Data model (core)

```mermaid
erDiagram
  User ||--o{ AuditEvent : writes
  Building ||--|{ Zone : has
  Zone ||--o{ Sensor : has
  Building ||--o{ TelemetryPoint : records
  Building ||--o| ConstraintPolicy : constrains
  Building ||--o| ComfortPolicy : comfort
  Building ||--o{ GoalProfile : goals
  Building ||--o{ ControlPlan : plans
  Building ||--o{ Decision : decides
  Decision ||--o{ PredictionLedgerEntry : tracks
  Building ||--o{ Alert : raises
  User ||--o{ AssistantConversation : chats
```

Primary entities are defined in `services/api/app/models/entities.py`. Runtime still calls `Base.metadata.create_all` on startup; Alembic is available for future migrations (`services/api/alembic`).

---

## Packages

| Path | Role |
|------|------|
| `packages/contracts` | Shared Zod enums / WS event schemas |
| `packages/api-client` | Thin typed REST stubs |
| `packages/config` | Shared TS config helpers |
| `packages/design-tokens` | Color / type tokens |
| `packages/eslint-config` | Minimal shared ESLint export |
