# Mock / Synthetic / Hardcoding Audit

**Commit:** `61ed36cc9bc89cd37ba7a38a1ec7b4d1e12702e1`  
**Search time:** 2026-07-25T10:54:48Z  
**Raw hits:** `search-raw.txt`

## Authoritative findings

### 1. Synthetic ×1.12 multiplier

| Location | Finding |
|----------|---------|
| `services/api/app/services/runtime.py` ~801 | Comment states ×1.12 **removed**; `_record_kpi_snapshot` uses factor 1.0 (no multiplier). |
| `apps/web/components/DataModeBanner.tsx:40` | UI text “No synthetic ×1.12 multiplier” |
| Docs | Multiple docs claim removal |

**Runtime verification required:** grep of production code paths for `* 1.12` assignment — none found in `runtime.py` calculation path in current tree.

**Status pending runtime:** PARTIALLY — source shows removal; Phase 12 must confirm dashboard does not invent savings.

### 2. Mock twin still present (expected for UI)

| Location | Role |
|----------|------|
| `services/simulator/twinpilot_simulator/mock.py` | `MockBuildingSimulator` |
| `scripts/run_demo.sh` | Defaults `SIMULATOR_PROVIDER=mock` |
| `Settings.simulator_provider` default | `"mock"` |

**Important:** Hackathon dashboard KPIs use `DATA_MODE` (default `energyplus` in `config.py:29`), which is **orthogonal** to `SIMULATOR_PROVIDER`. Demo script still starts mock twin for live zones while dashboard may overlay experiment JSON.

### 3. EnergyPlus mock fallback

| Location | Behaviour |
|----------|-----------|
| `energyplus.py` | Strict by default; mock only if `ENERGYPLUS_ALLOW_MOCK_FALLBACK=1` |
| Tests | `test_strict_adapter_raises_when_unconfigured` |

### 4. Numeric claim literals in docs/README

Values `421.51`, `416.00`, `1.31%`, etc. appear in **documentation** (`README.md`, `docs/results.md`, `FINAL_HACKATHON_READINESS_REPORT.md`).  
They must **not** appear as hardcoded dashboard return values — Phase 12 verifies API returns parsed JSON fields.

### 5. P0 — MCP path is simulated in LLM experiment

**File:** `scripts/llm_mcp_loop.py` lines 52–71

```python
def mcp_observation_from_energyplus(obs):
    """Simulate MCP resource/tool payload built from EnergyPlus observations.
    ...
    """
    resource = { "resource": "building://current-state", "tool": "get_building_state", ...}
    log_stage("mcp_resource_tool", {"ok": True, ...})
```

This does **not** import `twinpilot_mcp`, does **not** start the MCP server, and does **not** call `call_tool`/`read_resource`. It logs `mcp_resource_tool` with `ok: True` after local dict construction.

**Claim impact:** “Real LLM/MCP path using Ollama” — Ollama may be real; **MCP invocation in this script is NOT a real MCP server call** based on source inspection. Phase 9 must confirm at runtime (no MCP process).

### 6. DATA_MODE configuration

| Case | Behaviour (source) |
|------|---------------------|
| `DATA_MODE=energyplus` (default in Settings) | Serve `experiment_dashboard_payload` if results available |
| `DATA_MODE=mock` | Mock KPIs; savings forced to 0 |
| Invalid + `hackathon_mode` | Forced to `energyplus` |
| EnergyPlus mode + missing results | Falls through to mock-style status block with `data_mode: mock`? **Must verify** — `building_status` uses experiment only `if data_mode == energyplus and experiment.get("available")`; else returns mock block. **This may silently present mock-labeled KPIs when results missing while env says energyplus intent.** |

## Classification summary

| Pattern | Verdict |
|---------|---------|
| ×1.12 in live KPI math | Appears removed from code |
| Mock twin | Present; intentional for `SIMULATOR_PROVIDER=mock` |
| Silent EnergyPlus→mock in adapter | Blocked unless opt-in env |
| Dashboard hardcoded 421.51 | Not found in TS/Python API logic (docs only) |
| LLM MCP experiment MCP stage | **Simulated packaging — P0 claim defect** |
