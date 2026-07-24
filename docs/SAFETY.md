# TwinPilot Safety

TwinPilot treats safety as a **hard gate**, not a prompt. The **Safety Shield** (`twinpilot_optimizer.safety.SafetyShield`) validates every proposed control action before apply/override. LLM agents and UI code cannot bypass it.

This demo still actuates a **simulator**, not a live BMS. Do not treat it as production-certified.

---

## Operating modes

| Mode | Behavior |
|------|----------|
| **AUTONOMOUS** | Valid low-risk actions may auto-apply |
| **GUARDED** | Auto-apply only when confidence / checks allow |
| **ADVISORY** | Plans require human approval before apply |
| **FALLBACK** | Safe policy; critical faults / low confidence |
| **MANUAL** | Operator-driven; optimizer does not auto-apply |

Mode recommendations use deterministic thresholds in `twinpilot_optimizer.modes` (default autonomous ≥ 0.85, guarded ≥ 0.65, advisory ≥ 0.40). Critical sensor faults force FALLBACK. Administrators can PATCH mode with a reason (audited).

---

## What the Safety Shield checks

Implemented checks include:

1. **Finite numeric values** (reject NaN / Inf)
2. **Setpoint range** vs `ConstraintPolicy` (cooling/heating bounds)
3. **Max change per interval** (`max_setpoint_change_per_interval`)
4. **Duration cap** (`maximum_control_duration`)
5. **Minimum ventilation** when relevant
6. **Data freshness** vs `maximum_data_age_seconds`
7. **Required sensors healthy**
8. **Comfort violation minutes** from simulation
9. **Simulation OK** (blocks when forced sim failure / unavailable)
10. **State snapshot match** (`state_hash`)
11. **Plan expiry**
12. **Mode / approval** — ADVISORY & MANUAL require approved=true
13. **Autonomy confidence** vs `minimum_confidence_for_autonomy`
14. **Critical alert blocking** in FALLBACK

On success, the shield issues a **`validation_token`** bound to plan id + state hash. Apply paths re-validate and parse the token.

---

## Validation tokens

Format (opaque to clients): `v1:<plan_id>:<state_hash>:<issuer>:<timestamp>`.

- Produced by `validate` / plan validate endpoints
- Required for MCP `apply_validated_plan`
- API `apply` rejects missing/invalid tokens

---

## RBAC

Permissions are enforced in `app.core.deps.PERMISSIONS`. High-risk plan approval requires Facility Manager or Administrator. Viewers are read-only.

---

## Rollback

`POST /buildings/{id}/rollback` restores safe setpoints via the runtime hub, writes audit events, and emits `rollback.*` WebSocket events. Operators and above may invoke it.

---

## Demo scenarios that exercise safety

| Scenario | Expected signal |
|----------|-----------------|
| `faulty_sensor` | Confidence drop / FALLBACK pressure |
| `infeasible_target` | Infeasible / rejected plans |
| `simulation_failure` | Apply/sim blocked |
| `rollback` | Safe-policy restore |

---

## Explicit non-goals

- No unrestricted MCP tool (`set_any_actuator` is forbidden)
- No production BMS write path in this repo
- No claim of SIL / UL / building-code certification
