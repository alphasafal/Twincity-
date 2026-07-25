# Judge Q&A — prepared answers

## Did the LLM produce the 4.98% savings?

The primary quantitative result comes from the reproducible **Path A** deterministic optimisation experiment (comfort-zero policy). The LLM operates as a **supervisory agent** through MCP (Path C), selecting contextual strategies and proposing bounded actions. Numeric setpoints are computed by the deterministic optimiser; SafetyShield retains final authority. Path C hybrid runs prove the LLM is materially involved in closed-loop decisions without replacing Path A as the authoritative claim.

## Why not use only rules?

Rules are responsible for safety, but they do not provide flexible contextual planning, explanation or tool-based adaptation. The LLM selects strategies using occupancy, weather, thermal state and recent outcomes; deterministic components execute and enforce them safely.

## Why is total saving only 1.31%?

HVAC represents only part of this model’s total consumption. Lighting and equipment loads were unchanged. The controlled HVAC portion fell by **4.98%**, producing a **1.31%** total-building reduction.

## How do you prove the action reached EnergyPlus?

Runtime traces record observation → proposal → SafetyShield decision → executed `Clg-SetP-Sch` value → following EnergyPlus state for consecutive timesteps (`final-release/evidence/final-actuator-trace.csv`, `final-next-state-proof.md`, hybrid `stage_log.jsonl`).

## Is this connected to a real building?

No. The prototype closes the loop against an EnergyPlus digital building. Physical BMS integration is the next deployment step.

## What happens when AI fails?

The system detects Ollama or MCP failure and activates deterministic fallback. AI availability is not required for safe continued operation.

## What are Paths A / B / C?

| Path | Role |
|------|------|
| A | Authoritative comfort-zero savings (deterministic optimiser) |
| B | LLM structured setpoint proposals via separate MCP stdio |
| C | Hybrid: LLM selects ECM/strategy → optimiser → SafetyShield → actuator → self-correction |
