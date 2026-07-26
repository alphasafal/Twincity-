# Eco-Loop — Official IDEA PPT (exactly 6 slides)

**Rules:** max 6 slides including title · bullets / diagrams only · no long paragraphs · official template only · export **PDF** for HirePro.

**Live demo:** https://twinpilot.webyaar.in  
**GitHub:** https://github.com/alphasafal/Twincity-/tree/ecolooop-hackathon-final  
**Login:** `manager@twinpilot.demo` / `TwinPilot-Manager-Demo!`

Fill `[brackets]` from HirePro before export.

---

## SLIDE 1 — TITLE PAGE

**Problem Statement ID –** `[from HirePro]`  
**Problem Statement Title –** Eco-Loop Building Agents  
**Theme –** Building energy / Physical AI / Autonomous building agents  
**PS Category –** Software  
**Student Name (Registered on portal) –** Safal Gupta  
**Student ID –** `[from HirePro]`  

**Idea title:** Eco-Loop Building Agents  
**One-line:** Safe autonomous building optimisation through EnergyPlus, MCP and deterministic AI control  

**Links**
- Live PoC: https://twinpilot.webyaar.in
- Code: https://github.com/alphasafal/Twincity-/tree/ecolooop-hackathon-final

---

## SLIDE 2 — PROPOSED SOLUTION (idea + problem fit + innovation)

### Proposed solution (prototype)
- Physical-AI PoC: **EnergyPlus digital building** + **local OSS LLM** + **MCP tools** + **SafetyShield**
- Closed loop: Observe → Propose → Validate → Execute → Measure → Correct
- AI never writes actuators directly — SafetyShield is the only gate

### How it addresses the problem
- Fixed schedules → replaced by state-aware control (occupancy, weather, zone temps)
- Energy waste / peak → measured HVAC **4.98%** / total **1.31%** / peak **1.47%**
- Unsafe LLM control → range, rate-limit, deadband, sensor & fallback checks
- Observe-only dashboards → forward injection into live EnergyPlus (`Clg-SetP-Sch`)

### Innovation & uniqueness
- Hybrid authority split: LLM picks **strategy/ECM** · optimiser computes **numbers** · SafetyShield **decides**
- Real **stdio MCP** (separate process PIDs) — not in-process fake tools
- Self-correction: expected vs actual outcome after each EnergyPlus step
- Honest dual path: Path A = savings proof · Path C = LLM/MCP agency proof

```text
EnergyPlus ──obs──► MCP stdio ──► Ollama strategy
                         │
                         ▼
              Deterministic optimiser
                         │
                         ▼
                   SafetyShield
                         │
                         ▼
              Clg-SetP-Sch write ──► next state
```

---

## SLIDE 3 — TECHNICAL APPROACH (tech + methodology)

### Technologies
| Layer | Stack |
|-------|--------|
| Simulation | EnergyPlus 24.1 Runtime API (`pyenergyplus`) |
| Language | Python 3.12 · TypeScript / Next.js 15 (dashboard) |
| LLM | Local Ollama (`llama3.2:1b`) — open-source, self-hosted |
| Tool bus | MCP over **stdio** (`twinpilot-mcp`) |
| Control | Deterministic optimiser + SafetyShield |
| Models | `.idf` office + Chicago `.epw` |
| Evidence | JSON / JSONL / CSV under `results/` + `final-release/evidence/` |

### Methodology / process (implementation flowchart)
```text
1. Baseline EnergyPlus run (fixed schedules)
2. Agent / hybrid run (same IDF·EPW·occupancy·period)
3. Each hour:
   a. Read zones, outdoor, occupancy
   b. MCP tools/list + tools/call
   c. Ollama → strategy JSON  (or deterministic Path A)
   d. Optimiser → setpoint
   e. SafetyShield → approve | reject | fallback
   f. Write Clg-SetP-Sch · read next state
4. Compare baseline vs agent → % kWh + comfort
5. Dashboard shows measured results (DATA_MODE=energyplus)
```

### Code entry points (for engineers)
- EnergyPlus loop: `services/simulator/twinpilot_simulator/ep_experiment.py`
- Safety: `services/optimizer/twinpilot_optimizer/safety.py`
- MCP server: `services/mcp-server/twinpilot_mcp/energyplus_experiment_server.py`
- MCP client: `services/mcp-server/twinpilot_mcp/stdio_session.py`
- Path C hybrid: `scripts/hybrid_supervisory_loop.py`
- Tour: `docs/CODE_TOUR.md`

---

## SLIDE 4 — WORKING PROTOTYPE + ARTIFACTS

### Working prototype (snaps to show / attach)
- Live dashboard: https://twinpilot.webyaar.in/dashboard (measured KPIs)
- Actuator trace: `Clg-SetP-Sch` write = True → next zone °C
- MCP proof: client PID ≠ server PID · `initialize` / `tools/call`
- Safety snap: 35°C rejected · no actuator write
- Fallback snap: Ollama down → deterministic_fallback ×48 (still gated)
- Demo video ≤3 min: `Eco-Loop-Demo-Walkthrough.mp4`

### Relevant artifacts
| Artifact | Path |
|----------|------|
| Source code | GitHub branch (full monorepo) |
| Baseline IDF | `building-models/sample-office/office_5zone.idf` |
| Runtime-modified schedule | `final-release/evidence/building-models/` |
| Comparison export | `results/comparison/comparison.json` |
| Independent metrics | `final-release/evidence/independent-metrics.json` |
| Actuator CSV | `final-release/evidence/final-actuator-trace.csv` |
| MCP traces | `final-release/evidence/*mcp-runtime-trace.jsonl` |
| Hybrid self-correction | `final-release/evidence/hybrid/self_correction.jsonl` |
| Architecture | `docs/architecture.md` |
| Submission ZIP | `Eco-Loop-Hackathon-Submission.zip` |

### Path A verified results (comfort-zero)
| Metric | Baseline | Eco-Loop | Δ |
|--------|----------|----------|---|
| HVAC | 13.85 kWh | 13.16 kWh | **4.98%** |
| Total | 421.51 kWh | 416.00 kWh | **1.31%** |
| Peak | 19.93 kW | 19.64 kW | **1.47%** |
| Comfort | 0 h | 0 h | — |

---

## SLIDE 5 — FEASIBILITY AND VIABILITY

### Feasibility analysis
- Runs on local / cloud VM (no paid LLM API required)
- Open-source stack: EnergyPlus · Ollama · MCP · Next.js · FastAPI
- Reproducible scripts: `run_baseline.sh` · `run_agent.sh` · `run_hybrid_supervisory_experiment.sh`
- Clean-clone verified · dashboard honest no-data state (no silent mock)
- Safe degraded mode when LLM/MCP fails

### Viability
- Digital-building PoC proves control logic before physical BMS
- Clear path to BACnet / Modbus / Honeywell connectors (already scaffolded in repo)
- Operators keep approval / SafetyShield authority — deployable governance model

### Potential challenges & risks → strategies
| Challenge / risk | Strategy |
|------------------|----------|
| LLM invents unsafe setpoints | SafetyShield hard gate; LLM never actuates |
| LLM / Ollama down | Deterministic fallback; loop continues |
| MCP fake / in-process claims | Real stdio separate PIDs + protocol traces |
| Comfort vs savings tradeoff | Occupied caps · comfort-zero Path A claim |
| Long EnergyPlus logs | JSONL summaries · ZIP excerpts · regen scripts |
| Over-claiming savings | Publish measured Path A only (not Path B/C %) |
| Live demo offline | Named tunnel `twinpilot.webyaar.in` + offline video backup |

---

## SLIDE 6 — RESEARCH & REFERENCES + CLOSING

### Research & references (links)
- EnergyPlus / Runtime API — https://energyplus.net /
- Model Context Protocol (MCP) — https://modelcontextprotocol.io /
- Ollama (local OSS LLM) — https://ollama.com /
- Building energy context: buildings ≈ large share of global energy use (IEA / industry reports)
- Project evidence pack — `final-release/` + `Eco-Loop-Hackathon-Submission.zip`
- Live PoC — https://twinpilot.webyaar.in
- Source — https://github.com/alphasafal/Twincity-/tree/ecolooop-hackathon-final

### Closing points (speak these)
1. Real EnergyPlus closed loop with actuator write + next state  
2. OSS LLM + real MCP tools — SafetyShield remains authority  
3. Measured comfort-zero savings: **4.98% HVAC · 1.31% total · 0 comfort hours**  
4. Line: **AI proposes. SafetyShield validates. EnergyPlus executes.**

---

## Export checklist
1. Paste into official IDEA `.key` template (do not invent new section titles)
2. Keep **exactly 6 slides** (including title)
3. Bullets / diagrams only
4. Fill PS ID + Student ID
5. **File → Export → PDF**
6. Upload PDF on HirePro (no PPT / Word)
