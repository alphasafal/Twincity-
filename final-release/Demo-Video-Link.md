# Demo video

**Primary (in submission package):** `Eco-Loop-Demo-Walkthrough.mp4`  
**Repository path:** `final-release/demo-video/Eco-Loop-Demo-Walkthrough.mp4`  
**GitHub:** https://github.com/alphasafal/Twincity-/blob/main/final-release/demo-video/Eco-Loop-Demo-Walkthrough.mp4

Duration: **~3:00** (≤180s).

## Narrative shown (problem-statement closed loop)

1. MCP stdio session — separate client/server PIDs (`mcp_pids_differ: true`)
2. EnergyPlus observation → `tools/call get_building_observation`
3. Ollama strategy / ECM → `select_energy_conservation_measure`
4. Deterministic optimiser + SafetyShield approve
5. Forward injection: `Clg-SetP-Sch` write → next EnergyPlus zone temperature
6. Path A measured savings: HVAC **4.98%** · total **1.31%** · peak **1.47%** · comfort **0 h**
7. Unsafe 35°C rejected (no actuator write)
8. Ollama-down deterministic fallback (still SafetyShield-gated)

Source storyboard: `final-release/demo-video/live-closed-loop-demo.html`  
Talk track: `final-release/FINAL_DEMO_SCRIPT.md`

Regenerate:

```bash
# see scripts/render_submission_assets.sh or re-run live demo capture steps
```
