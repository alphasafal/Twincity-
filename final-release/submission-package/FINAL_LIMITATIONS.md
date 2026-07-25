# Final Limitations

**Commit:** `f0f94d84d08969784cf2373ddbb3cca6e3fa909b` · **Generated:** 2026-07-25T12:01:39.455435+00:00

1. EnergyPlus digital-building scope only — no physical BMS connector.
2. No BACnet/BMS actuation path in this prototype.
3. Results are model/weather/period specific (sample office + Chicago EPW demo period).
4. Local Ollama dependency for the LLM path (`llama3.2:1b` tested).
5. Carbon uses a static configured emission factor (estimate).
6. Limited evaluated scenarios; Path A comfort-zero is the authoritative claim set.
7. Prototype security boundaries (demo JWT users, local stdio MCP).
8. Production hardening remaining (authz, observability, drift monitoring).
9. Real-world commissioning and facility-operator approval required before any plant use.
10. LLM-path energy outcomes vary; do not substitute them for Path A claims.
