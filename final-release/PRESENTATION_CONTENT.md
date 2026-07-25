# Presentation Content (6 slides)

**Commit:** `133b0530670f2ed5b9fcf011d7a0adaa0b63228c`

## Slide 1 — Problem and objective
- **Message:** Unsafe autonomy is unacceptable; measurable gated autonomy is the goal.
- Bullets: HVAC waste; raw LLM risk; need reproducible loop; comfort hard constraint; prove EnergyPlus gating.
- **Visual:** simple waste/comfort tension graphic.
- **Speaker notes:** Emphasize digital building, not plant control.
- **Evidence:** README.

## Slide 2 — Eco-Loop solution
- **Message:** AI proposes. SafetyShield validates. EnergyPlus executes.
- Bullets: Runtime API observe; optional MCP+Ollama; deterministic shield; Clg-SetP-Sch only if approved; fair baseline compare.
- **Visual:** one horizontal flow.
- **Evidence:** docs/architecture.md.

## Slide 3 — Technical architecture
- **Message:** Separate processes; authoritative safety.
- Bullets: EnergyPlus observations; MCP client≠server PID; Ollama JSON proposals; SafetyShield; DATA_MODE=energyplus dashboard.
- **Visual:** process/PID diagram.
- **Evidence:** mcp-process-proof.md.

## Slide 4 — Working prototype
- **Message:** Closed loop is real.
- Bullets: fresh scripts; actuator+next-state; stdio MCP; honest no-data UI; clean-clone path.
- **Visual:** terminal + dashboard placeholders.
- **Evidence:** actuator trace; dashboard proofs.

## Slide 5 — Verified results
- **Message:** Comfort-zero savings on identical inputs.
- Bullets: total 1.31%; HVAC 4.98%; peak 1.47%; comfort 0/0; actions 48/0/0.
- **Visual:** before/after bars.
- **Optional aside:** aggressive policy saved more HVAC but violated comfort — not selected.
- **Evidence:** independent-metrics.json.

## Slide 6 — Safety, limitations and future deployment
- **Message:** Prototype today; commissioning required tomorrow.
- Bullets: 35°C reject; Ollama fallback; digital-only; carbon estimate; operator approval; next BMS connector.
- **Visual:** shield + limitations.
- **Evidence:** FINAL_LIMITATIONS.md.
