# Final Owner Checklist

**Commit:** `f0f94d84d08969784cf2373ddbb3cca6e3fa909b`  
**Branch:** `cursor/ecolooop-energyplus-audit-b6b3`  
**Generated:** 2026-07-25T12:01:39.455435+00:00

Use this as a non-expert runbook. Check boxes only after you personally observe success.

## [ ] Confirm exact final Git commit
- **Command:** `git rev-parse HEAD`
- **Proves:** Matches FINAL_RELEASE_MANIFEST.json
- **Success looks like:** SHA shown equals sealed commit
- **Failure looks like:** SHA differs / detached unexpected
- **Evidence to inspect:** `FINAL_RELEASE_MANIFEST.json`

## [ ] Confirm working tree is clean
- **Command:** `git status`
- **Proves:** No unexpected dirty files before tag
- **Success looks like:** clean working tree
- **Failure looks like:** unexpected modifications
- **Evidence to inspect:** `logs/repository-state.txt`

## [ ] Run prerequisite checker
- **Command:** `./scripts/check_prerequisites.sh`
- **Proves:** Environment ready
- **Success looks like:** RESULT: PASS
- **Failure looks like:** RESULT: FAIL
- **Evidence to inspect:** `logs/prerequisites.log`

## [ ] Run baseline experiment
- **Command:** `./scripts/run_baseline.sh`
- **Proves:** EnergyPlus baseline completes
- **Success looks like:** simulation_status completed ~421.51 kWh
- **Failure looks like:** failed / fatal
- **Evidence to inspect:** `evidence/energyplus/baseline-summary.json`

## [ ] Run agent experiment
- **Command:** `./scripts/run_agent.sh`
- **Proves:** Closed-loop agent completes
- **Success looks like:** completed; 48 decisions; comfort 0
- **Failure looks like:** failed / comfort>0 unexpectedly
- **Evidence to inspect:** `evidence/energyplus/agent-summary.json`

## [ ] Run comparison
- **Command:** `./scripts/compare_results.sh`
- **Proves:** Fair delta report
- **Success looks like:** comparison.json written
- **Failure looks like:** missing inputs
- **Evidence to inspect:** `evidence/energyplus/comparison.json`

## [ ] Inspect fresh result timestamps
- **Command:** `ls -l results/*/summary.json`
- **Proves:** Artifacts from this release run
- **Success looks like:** mtimes match release window
- **Failure looks like:** old/stale files
- **Evidence to inspect:** `logs/energyplus-generated-files.txt`

## [ ] Inspect five consecutive actuator rows
- **Command:** `column -t -s, final-release/evidence/final-actuator-trace.csv | head`
- **Proves:** Closed-loop continuity
- **Success looks like:** 5+ rows write=True with next temps
- **Failure looks like:** missing next state
- **Evidence to inspect:** `evidence/final-actuator-trace.csv`

## [ ] Confirm Clg-SetP-Sch is written
- **Command:** `rg energyplus_actuator_written results/agent/actions.json | head`
- **Proves:** Actuator path exercised
- **Success looks like:** true on approved rows
- **Failure looks like:** all false
- **Evidence to inspect:** `evidence/final-next-state-proof.md`

## [ ] Confirm next EnergyPlus state is returned
- **Command:** `sed -n '1,8p' final-release/evidence/final-next-state-proof.md`
- **Proves:** Next timestep observation
- **Success looks like:** PASS verdict
- **Failure looks like:** FAIL verdict
- **Evidence to inspect:** `evidence/final-next-state-proof.md`

## [ ] Confirm MCP client and server PIDs differ
- **Command:** `python -c "import json;s=json.load(open('results/llm_mcp/summary.json'));print(s['mcp_client_pid'],s['mcp_server_pid'],s['mcp_pids_differ'])"`
- **Proves:** Separate process MCP
- **Success looks like:** pids_differ True
- **Failure looks like:** same PID / missing
- **Evidence to inspect:** `evidence/mcp-process-proof.md`

## [ ] Inspect initialize, tools/list and tools/call
- **Command:** `rg -n 'initialize|tools/list|tools/call' final-release/evidence/mcp-runtime-trace.jsonl | head`
- **Proves:** Real MCP protocol
- **Success looks like:** events present
- **Failure looks like:** empty trace
- **Evidence to inspect:** `evidence/mcp-runtime-trace.jsonl`

## [ ] Confirm Ollama returns a structured proposal
- **Command:** `head -3 final-release/evidence/ollama-structured-responses.jsonl`
- **Proves:** Local model proposals
- **Success looks like:** proposed_cooling_setpoint_c present
- **Failure looks like:** no rows
- **Evidence to inspect:** `evidence/ollama-runtime-proof.md`

## [ ] Trigger 35°C unsafe action
- **Command:** `rg -n safety_shield_rejects_unsafe results/llm_mcp/stage_log.jsonl`
- **Proves:** Unsafe proposal path
- **Success looks like:** proposed 35
- **Failure looks like:** missing stage
- **Evidence to inspect:** `evidence/safety-rejection.log`

## [ ] Observe SafetyShield rejection
- **Command:** `cat final-release/evidence/safety-rejection.log`
- **Proves:** Reject reasons recorded
- **Success looks like:** approved=False disposition=rejected
- **Failure looks like:** approved=True
- **Evidence to inspect:** `evidence/safety-rejection.log`

## [ ] Trigger Ollama failure
- **Command:** `OLLAMA_BASE_URL=http://127.0.0.1:1 RESULTS_LLM_DIR=/tmp/llm_fail_test ./scripts/run_llm_mcp_experiment.sh`
- **Proves:** Unavailable model path
- **Success looks like:** connection refused logged
- **Failure looks like:** silent success with mock
- **Evidence to inspect:** `evidence/ollama-fallback.log`

## [ ] Observe deterministic fallback
- **Command:** `cat final-release/evidence/ollama-fallback.log`
- **Proves:** Fallback counts
- **Success looks like:** fallback=48
- **Failure looks like:** fallback=0 with failures
- **Evidence to inspect:** `evidence/ollama-fallback.log`

## [ ] Restore Ollama and observe recovery
- **Command:** `curl -s http://127.0.0.1:11434/api/tags | head`
- **Proves:** Service recovery
- **Success looks like:** llama3.2:1b listed; MCP session opens
- **Failure looks like:** still down
- **Evidence to inspect:** `evidence/recovery-after-failure.md`

## [ ] Test dashboard no-data state
- **Command:** `see FINAL_COMMAND_REFERENCE / move results aside`
- **Proves:** Honest unavailable UX
- **Success looks like:** energyplus_results_unavailable
- **Failure looks like:** mock KPIs appear
- **Evidence to inspect:** `evidence/dashboard-no-data-proof.md`

## [ ] Test dashboard real-data state
- **Command:** `DATA_MODE=energyplus ./scripts/run_demo.sh`
- **Proves:** Measured KPIs
- **Success looks like:** energyplus_experiment_results; ~1.31% total
- **Failure looks like:** wrong multiplier / mock
- **Evidence to inspect:** `evidence/dashboard-real-data-proof.md`

## [ ] Inspect dashboard API response
- **Command:** `curl authenticated /buildings/{id}/status`
- **Proves:** API lineage
- **Success looks like:** reductions match comparison.json
- **Failure looks like:** mismatch / 1.12
- **Evidence to inspect:** `evidence/dashboard-api-samples/`

## [ ] Stop backend and observe honest failure state
- **Command:** `stop uvicorn; reload dashboard`
- **Proves:** No invented live data
- **Success looks like:** API errors / stale notice
- **Failure looks like:** fake live KPIs continue updating
- **Evidence to inspect:** `evidence/dashboard-disconnection-proof.md`

## [ ] Complete clean-clone test
- **Command:** `bash scripts/_final_clean_clone_run.sh`
- **Proves:** README-only reproducibility
- **Success looks like:** CLEAN_CLONE_STATUS=PASS
- **Failure looks like:** undocumented blockers
- **Evidence to inspect:** `evidence/clean-clone-report.md`

## [ ] Run final smoke test
- **Command:** `./scripts/final_smoke_test.sh`
- **Proves:** Pre-demo readiness
- **Success looks like:** SMOKE RESULT: PASS
- **Failure looks like:** FAIL
- **Evidence to inspect:** `logs/`

## [ ] Build final evidence package
- **Command:** `python scripts/build_submission_evidence.py`
- **Proves:** Judge bundle inputs
- **Success looks like:** submission-evidence written
- **Failure looks like:** script error
- **Evidence to inspect:** `submission-package/`

## [ ] Confirm no secrets
- **Command:** `./scripts/final_submission_check.sh`
- **Proves:** Hygiene
- **Success looks like:** PASS secret scan
- **Failure looks like:** secret-like hit
- **Evidence to inspect:** `SECURITY_AND_PRIVACY_CHECK.md`

## [ ] Confirm no generated results are tracked
- **Command:** `git ls-files results submission-evidence`
- **Proves:** Repo cleanliness
- **Success looks like:** gitkeep only
- **Failure looks like:** json/csv tracked
- **Evidence to inspect:** `logs/hygiene-scan.txt`

## [ ] Record backup demonstration video
- **Command:** `(owner camera/screen recorder)`
- **Proves:** Offline demo backup
- **Success looks like:** video covers loop+results+safety
- **Failure looks like:** missing backup
- **Evidence to inspect:** `submission-package/placeholders/demo-video.txt`

## [ ] Review final presentation
- **Command:** `open PRESENTATION_CONTENT.md`
- **Proves:** Talk track ready
- **Success looks like:** 6 slides match Path A numbers
- **Failure looks like:** stale 12.20% claim
- **Evidence to inspect:** `PRESENTATION_CONTENT.md`

## [ ] Create final release tag manually
- **Command:** `git tag -a hackathon-final-v1 -m 'Verified Eco-Loop hackathon release'`
- **Proves:** Immutable pointer
- **Success looks like:** tag on sealed commit
- **Failure looks like:** tag on wrong SHA
- **Evidence to inspect:** `FINAL_RELEASE_REPORT.md`

## [ ] Push only after owner approval
- **Command:** `git push -u origin cursor/ecolooop-energyplus-audit-b6b3; git push origin hackathon-final-v1`
- **Proves:** Remote publish
- **Success looks like:** owner-approved push
- **Failure looks like:** accidental push
- **Evidence to inspect:** `FINAL_RELEASE_REPORT.md`
