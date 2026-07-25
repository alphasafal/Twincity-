# Clean-Room Documentation Gaps (Phase 14)

1. `results/` JSON artifacts are committed (~74 tracked files)
2. EnergyPlus binary not in git — setup_energyplus.sh required
3. Ollama assumed for LLM experiment
4. run_demo.sh still announces "simulated data"
5. Readonly SQLite path breaks login (env-specific)
6. Integration tests need PYTHONPATH=services/api
7. LLM script claims MCP but simulates payload packaging
