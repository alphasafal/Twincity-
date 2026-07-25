# Final Command Reference

**Commit:** `39cb4da36b9f79de36aa797de28de5bb0a76f950`
**Branch:** `cursor/ecolooop-energyplus-audit-b6b3`

## Prerequisites / setup
```bash
./scripts/check_prerequisites.sh
./scripts/setup.sh
./scripts/setup_energyplus.sh
```

## Path A (authoritative comfort-zero)
```bash
./scripts/run_baseline.sh
./scripts/run_agent.sh
./scripts/compare_results.sh
```

## Path B (LLM + stdio MCP)
```bash
unset RESULTS_LLM_DIR TWINPILOT_MCP_TRACE TWINPILOT_MCP_EVIDENCE_DIR
./scripts/run_llm_mcp_experiment.sh
```

## Safety / fallback
```bash
# 35C rejection is logged by llm_mcp_loop at end of a normal run
OLLAMA_BASE_URL=http://127.0.0.1:1 RESULTS_LLM_DIR=/tmp/llm_fail_test ./scripts/run_llm_mcp_experiment.sh
```

## Dashboard / live demo
```bash
DATA_MODE=energyplus ./scripts/run_demo.sh
# http://localhost:3000/dashboard
# http://localhost:3000/live-demo
```

## Evidence / acceptance
```bash
python scripts/build_submission_evidence.py
./scripts/final_smoke_test.sh
./scripts/final_acceptance.sh
./scripts/final_submission_check.sh
```

## Inspect MCP PIDs / traces / actuator
```bash
python -c "import json;s=json.load(open('results/llm_mcp/summary.json'));print(s['mcp_client_pid'],s['mcp_server_pid'],s['mcp_pids_differ'])"
rg -n "initialize|tools/list|tools/call" final-release/evidence/mcp-runtime-trace.jsonl | head
column -t -s, final-release/evidence/final-actuator-trace.csv | head
```

## Git hygiene / tag (owner only)
```bash
git ls-files results submission-evidence
git status
git rev-parse HEAD
git tag -a hackathon-final-v1 -m "Verified Eco-Loop hackathon release"
# ONLY after owner approval:
# git push -u origin cursor/ecolooop-energyplus-audit-b6b3
# git push origin hackathon-final-v1
```
