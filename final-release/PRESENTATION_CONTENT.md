# Presentation Content (6 slides max, including title)

**Rendered PDF:** `final-release/presentation/Eco-Loop-Presentation.pdf`  
**Editable HTML:** `final-release/presentation/eco-loop-slides.html`  
Regenerate: `./scripts/render_submission_assets.sh`

**Tagline:** Safe autonomous building optimisation through EnergyPlus, MCP and deterministic AI control.

## Slide 1 — Title

**Eco-Loop Building Agents**

- Problem Statement ID / title / theme / software category (fill from template)
- Team / member names / student IDs (fill from template)
- Tagline: Safe autonomous building optimisation through EnergyPlus, MCP and deterministic AI control.

## Slide 2 — Problem and proposed solution

**Problem**
- Fixed HVAC schedules ignore dynamic occupancy and weather
- Buildings waste energy and contribute to peak demand
- Uncontrolled LLM decisions can be unsafe
- Existing dashboards observe but do not close the loop

**Solution**
Eco-Loop observes, reasons, validates, acts and measures outcomes in an EnergyPlus digital building.

**Visual:** Observe → Propose → Validate → Execute → Measure → Correct

## Slide 3 — Technical architecture

```text
EnergyPlus → observations → MCP client → stdio → separate MCP server
  → Ollama supervisory agent (strategy/ECM)
  → Deterministic optimiser → SafetyShield → Clg-SetP-Sch
  → Next EnergyPlus state → self-correction
```

Highlight: real actuator write · separate MCP process · local open-source LLM · safe fallback · audit log

Honest paths: **A** deterministic savings · **B** LLM setpoint demo · **C** hybrid supervisory (LLM selects strategy)

## Slide 4 — Working prototype

Screenshots: dashboard `DATA_MODE=energyplus` · `/live-demo` · MCP tools/call · actuator trace · 35°C rejection

Minimal text:
- 48 normal control actions (Path A)
- Real EnergyPlus results
- 35°C proposal rejected
- Ollama failure handled by fallback
- Path C: LLM strategy → optimiser → SafetyShield → next state

## Slide 5 — Verified results and evaluation

| Metric | Baseline | Eco-Loop | Improvement |
|--------|----------|----------|-------------|
| HVAC energy | 13.85 kWh | 13.16 kWh | **4.98%** |
| Total energy | 421.51 kWh | 416.00 kWh | **1.31%** |
| Peak power | 19.93 kW | 19.64 kW | **1.47%** |
| Comfort violations | 0 h | 0 h | — |
| Comfort degree-hours | 0 | 0 | — |

**Key line:** Energy savings without sacrificing occupied-zone comfort.

Fairness: same IDF · same EPW · same occupancy · same period · controller is the intended difference.

Multi-scenario (Path A controller): normal summer / hot peak / high occupancy — all comfort-zero with HVAC savings ~5%.

## Slide 6 — Feasibility, limitations and future scope

**Feasibility:** local/cloud VM · open-source LLM · reproducible scripts · clean-clone verified · safe degraded mode

**Limitations:** EnergyPlus digital building only · no physical BMS yet · scenario-specific savings

**Future:** BACnet/Modbus · campus-scale · dynamic tariffs/carbon · physical pilot

QR: GitHub · demo video · optional live dashboard
