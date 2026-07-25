# MCP Transport Remediation Report

Generated: `2026-07-25T11:22:21.838169+00:00`  
Pre-remediation commit: `b63311c3f929a8d9a85dfbf8ed5845231c486b6b`

## 1. Preserved original evidence

- Prior independent audit under `manual-verification/` retained.
- Original in-process MCP findings copied to `mcp-transport/preserved-09-llm-mcp-original/`.
- Earlier FAILED / PARTIALLY VERIFIED Phase 9 conclusions are **not rewritten**; this report is before/after.

### Before (original)

- Authoritative LLM path called `twinpilot_mcp.handlers.call_tool` **in-process**.
- Claim “MCP invoked” was **FAILED** / later **PARTIALLY VERIFIED** after that in-process change.
- Generated `results/` JSON was tracked in Git (~74 files).
- Clean clone could be pre-seeded with experiment outputs.
- README implied stronger MCP isolation than implemented.

## 2. After (this remediation)

### Real stdio MCP

- Server: `python -m twinpilot_mcp` with `TWINPILOT_MCP_MODE=energyplus_experiment`
- Client: `twinpilot_mcp.stdio_session.StdioMcpSession` (spawns child, MCP initialize, tools/list, tools/call)
- Authoritative script: `scripts/llm_mcp_loop.py` — **no** direct handler import
- Fresh run PIDs: client **38195** ≠ server **38200**
- Trace: `mcp-transport/mcp-runtime-trace.jsonl` (initialize, tools/list, 240 call pairs)

### Results untracked

- Git now tracks only `results/**/.gitkeep` (count=5)
- `.gitignore` ignores generated experiment/submission artifacts

### Honest no-data dashboard

- Empty `RESULTS_DIR` + `DATA_MODE=energyplus` → `data_label=energyplus_results_unavailable`
- Message: “No EnergyPlus experiment results found…”
- `energy_saved_today_pct=null` (not mock)
- After fresh experiments: dashboard matches raw summaries ({'data_mode': 'energyplus', 'available': True, 'baseline_match': True, 'agent_match': True, 'no_multiplier': True})

### Prerequisites

- `./scripts/check_prerequisites.sh` PASS (Ollama + `llama3.2:1b` verified)

### MCP failure matrix

{"total": 8, "passed": 8, "failed": []}

### Fresh deterministic metrics

{
  "baseline_ts": "2026-07-25T11:22:06.921990+00:00",
  "agent_ts": "2026-07-25T11:22:07.546063+00:00",
  "baseline_total": 421.5057,
  "agent_total": 415.9999,
  "comfort_agent": 0.0,
  "actions": {
    "approved": 48,
    "rejected": 0,
    "fallback": 0,
    "total_decisions": 48
  },
  "baseline_summary_sha256": "8600ab8306c4fbf0cc191f29c9184127cdad867bba2b1d1049938a03b8756698",
  "agent_summary_sha256": "62ea9542e1a95ac3d3277d18a35ebb2040e624ed4af6e2ef0dc4cd317dff815c",
  "comparison_sha256": "d632b17057fb68689496b31fae2c4af7dbfa3d8d7fe0c21b6c89c530469953f6"
}

## 3. Acceptance gates

| Gate | Status |
|------|--------|
| MCP client/server different PIDs | PASS |
| MCP initialization captured | PASS |
| tools/list captured | PASS |
| tools/call captured over stdio | PASS |
| Authoritative path no direct handler call | PASS |
| Killing MCP server detected failure | PASS |
| No generated results tracked by Git | PASS |
| Fresh dashboard honest no-data | PASS |
| Fresh experiments populate dashboard | PASS |
| Ollama prerequisite checker | PASS |
| Comfort remains 0 (deterministic) | PASS (0.0) |
| No silent mock fallback | PASS |

Clean-room clone workflow: see `mcp-transport/clean-room-stdio/` (populated next).
