# Limitations

1. **Interactive API/dashboard defaults to mock twin.** Real EnergyPlus closed-loop evidence is produced by `scripts/run_*.sh`, not by the 5-second UI control loop.
2. **EnergyPlus adapter `simulate_plan` for interactive UI** anchors to the last experiment metrics; it does not re-run a full co-simulation per plan click (too heavy for demo UX).
3. **Carbon is an estimate** (fixed kg/kWh factor), not a live grid-intensity feed.
4. **Comfort violation hours** in experiment summaries use occupied-hour heuristics from Date/Time + zone temperatures; they are reproducible but simplified vs full ASHRAE comfort models.
5. **No production BMS/BACnet/Honeywell connector** in this repository.
6. **Ollama** may produce invalid JSON on tiny models; system falls back to deterministic agent — never to uncontrolled actuation.
7. **Alembic** has no revision history; schema is `create_all` at startup.
8. **third_party/EnergyPlus** is not committed (large binary); evaluators run `./scripts/setup_energyplus.sh`.
9. Agent experiment may trade a small comfort penalty for energy savings — reported, not hidden.
10. MCP forecasts may be synthesized when forecast APIs are absent — labeled in MCP docs.
