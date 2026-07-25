# Maximum three-minute demonstration video script

Aim ≈ 2:45. Show data moving EnergyPlus → LLM/MCP → action → next state. Do not submit only a dashboard tour.

## 0:00–0:20 — Problem

“Commercial HVAC systems often use fixed schedules even though occupancy, weather and thermal conditions change continuously.”

Show building/dashboard briefly.

## 0:20–0:45 — Architecture

“Eco-Loop combines EnergyPlus, a separate MCP server, a local Ollama model, a deterministic optimiser and SafetyShield.”

Say: **AI proposes. SafetyShield validates. EnergyPlus executes.**

## 0:45–1:30 — Actual loop (Path C hybrid)

Show an actual run or accelerated trace:

1. EnergyPlus observation appears  
2. MCP `tools/call`  
3. Ollama structured strategy proposal  
4. Deterministic optimiser setpoint  
5. SafetyShield decision  
6. `Clg-SetP-Sch` actuator update  
7. Following EnergyPlus state / self-correction

## 1:30–2:00 — Results

Dashboard with Path A numbers:

“Eco-Loop reduced HVAC energy by **4.98%** and peak power by **1.47%**, while maintaining zero comfort violations.”

## 2:00–2:30 — Safety and fallback

- 35°C proposal → rejection → safe value retained  
- Ollama failure → deterministic fallback  

## 2:30–3:00 — Impact

“Eco-Loop demonstrates a practical path from passive building monitoring to safe, auditable and autonomous building operation.”
