# TwinPilot 7-Minute Demo Script

**Audience:** facility operators, product reviewers, hackathon judges  
**Setup:** `make setup && make demo` → http://localhost:3000  
**Login:** `manager@twinpilot.demo` / `TwinPilot-Manager-Demo!`  
**Framing:** All KPIs are from a **simulated** twin unless you configured EnergyPlus.

---

## Minute 0–1 — Hook & dashboard (≈60s)

1. Open the **Dashboard**. Point out the brand: TwinPilot — verifiable autonomous optimization.
2. Call out live load, estimated savings %, comfort compliance, and the **operating mode** badge (likely AUTONOMOUS).
3. Emphasize the confidence breakdown and that values are labeled **simulated**.

**Talk track:** “TwinPilot proposes actions, but nothing executes without the Safety Shield — and you can always see why.”

---

## Minute 1–2 — Digital twin & zones (≈60s)

1. Open **Digital Twin** / **Zones**. Show zone temperatures, setpoints, occupancy.
2. Click a zone (e.g. Core Office). Show telemetry sparkline + sensor health.
3. Mention WebSocket live updates (or polling fallback).

---

## Minute 2–3:30 — Optimization & Safety Shield (≈90s)

1. Go to **Optimization**. Generate candidate plans (balanced weights).
2. Open a plan card: objective score, predicted metrics, actions.
3. Run **Simulate** → **Validate**. Show checks + `validation_token`.
4. Optionally **Approve** / **Apply** (manager role). Show decision created.

**Talk track:** “Validate is independent of the planner. Apply re-checks the token and state hash.”

---

## Minute 3:30–5 — Scenario: faulty sensor → fallback (≈90s)

1. Open **Simulator** controls.
2. Start scenario **`faulty_sensor`**.
3. Watch confidence drop, alerts, and mode pressure toward **FALLBACK** / advisory behavior.
4. Show **Alerts** page; acknowledge one.

**Talk track:** “When sensors fail, autonomy yields. We don’t keep optimizing blindly.”

---

## Minute 5–6 — Rollback & ledger (≈60s)

1. Trigger **`rollback`** scenario or press **Safe Rollback**.
2. Confirm setpoints restore; show audit / decision rollback status.
3. Open **Analytics** / **Prediction Ledger** — predicted vs realized entries.

---

## Minute 6–7 — Assistant + close (≈60s)

1. Open **Assistant**. Ask: “Why was the last decision made?”
2. Note deterministic answers by default; Ollama optional for richer prose.
3. Close with limitations: simulated demo, EnergyPlus/Ollama optional, **not production-certified**, no live Honeywell BMS in this repo.

**Optional if time:** start `infeasible_target` to show rejected/infeasible plans, or show MCP catalog (`python -m twinpilot_mcp --catalog`).

---

## Checklist before presenting

- [ ] API `/health` OK
- [ ] Web login works
- [ ] Control loop producing telemetry
- [ ] Demo scenarios list loads
- [ ] Know which provider is active (`mock` vs `energyplus`, `deterministic` vs `ollama`)
