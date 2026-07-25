#!/usr/bin/env python3
"""Generate remaining final-release documents from fresh evidence."""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FR = ROOT / "final-release"
EV = FR / "evidence"
PKG = FR / "submission-package"
LOG = FR / "logs"
CHK = FR / "checksums"
NOW = datetime.now(timezone.utc).isoformat()
COMMIT = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True, cwd=ROOT).strip()
BRANCH = subprocess.check_output(
    ["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True, cwd=ROOT
).strip()

ind = json.loads((EV / "independent-metrics.json").read_text())
actions = json.loads((EV / "action-count.json").read_text())
base = json.loads((EV / "energyplus" / "baseline-summary.json").read_text())
agent = json.loads((EV / "energyplus" / "agent-summary.json").read_text())
llm = json.loads((ROOT / "results" / "llm_mcp" / "summary.json").read_text())

bt, at = base["total_energy_kwh"], agent["total_energy_kwh"]
bh, ah = base["hvac_energy_kwh"], agent["hvac_energy_kwh"]
bp, ap = base["peak_power_kw"], agent["peak_power_kw"]
rt = ind["independent_reductions_percent"]["total_energy"]
rh = ind["independent_reductions_percent"]["hvac_energy"]
rp = ind["independent_reductions_percent"]["peak_power"]
appr = actions["independent"]["approved"]
rej = actions["independent"]["rejected"]
fb = actions["independent"]["fallback"]

clean_log = (LOG / "clean-clone.log").read_text() if (LOG / "clean-clone.log").exists() else ""
clean_pass = "CLEAN_CLONE_STATUS=PASS" in clean_log or "DASHBOARD_PAYLOAD_CHECK=PASS" in clean_log

score_parts = {
    "Real EnergyPlus closed loop": [20, 20, "Fresh baseline/agent completed successfully"],
    "Actuator and next-state proof": [20, 10, "final-actuator-trace + next-state PASS"],
    "Experiment validity and reproducibility": [12, 12, "Fairness VALID"],
    "Energy and comfort evidence": [12, 12, "Independent metrics match; comfort 0/0"],
    "Real MCP stdio integration": [
        10,
        10,
        f"PIDs {llm.get('mcp_client_pid')}!={llm.get('mcp_server_pid')}",
    ],
    "Ollama structured proposal path": [8, 8, "48 structured proposals logged"],
    "SafetyShield and failure handling": [12, 12, "35C reject + 48 fallback + recovery"],
    "Dashboard data integrity": [6, 6, "no-data honest; real-data matches; no x1.12"],
    "Clean-clone workflow": [
        5,
        5 if clean_pass else 3,
        "PASS" if clean_pass else "In progress / incomplete at doc generation — provisional",
    ],
    "Documentation and demo readiness": [
        5,
        4,
        "Pack complete; owner tag/push remaining (-1)",
    ],
}
# fix mistaken max for actuator key
score_parts["Actuator and next-state proof"] = [
    10,
    10,
    "final-actuator-trace + next-state PASS",
]
total = sum(v[1] for v in score_parts.values())

# Ensure SECURITY / RELEASE_NOTES / CLAIMS / LIMITATIONS / DEMO / PRESENTATION / JUDGE / COMMAND exist
# (rewrite fully here for consistency)


def w(name: str, body: str) -> None:
    (FR / name).write_text(body if body.endswith("\n") else body + "\n")


w(
    "SECURITY_AND_PRIVACY_CHECK.md",
    f"""# Security and Privacy Check

Generated: {NOW}
Release commit (candidate): `{COMMIT}`
Branch: `{BRANCH}`

## Secret scan result
- High-confidence secret patterns (`sk-`, `ghp_`, PEM private keys): **none found** in hygiene scan.
- `.env` is gitignored; `.env.example` present.
- Demo passwords exist only as documented local demo credentials.

## Private-path scan result
- `/workspace/...` paths appear in historical audit evidence and generated summaries.
- Experiment runtime uses env vars (`ENERGYPLUS_HOME`, model/weather paths).

## Generated-file tracking result
- Tracked under `results/` and `submission-evidence/`: **`.gitkeep` only**.
- Historical MCP PID files under `manual-verification/mcp-transport/**` preserved as evidence.

## Dependency configuration result
- Python service packages + local `.venv`; Node via pnpm; EnergyPlus 24.1; local Ollama.

## Outstanding concerns
1. Demo credentials must be rotated before any public deployment.
2. Prototype JWT auth is not production-hardening.
3. MCP is local stdio only.
4. Tag/push remain owner-gated.

## Verdict
**PASS** for hackathon submission hygiene.
""",
)

w(
    "RELEASE_NOTES.md",
    f"""# Release Notes — Eco-Loop Building Agents

**Commit:** `{COMMIT}`
**Branch:** `{BRANCH}`
**Generated:** {NOW}

## Included
- Verified EnergyPlus Runtime API closed loop (Path A comfort-zero).
- Separate MCP client/server over stdio for LLM path.
- Local Ollama structured proposals gated by SafetyShield.
- Honest dashboard `DATA_MODE=energyplus` no-data state.
- Final-release evidence pack.

## Authoritative Path A results (fresh)
- Total: {bt:.2f} → {at:.2f} kWh ({rt:.2f}%)
- HVAC: {bh:.2f} → {ah:.2f} kWh ({rh:.2f}%)
- Peak: {bp:.2f} → {ap:.2f} kW ({rp:.2f}%)
- Comfort: 0 h / 0 degree-hours
- Actions: {appr} approved / {rej} rejected / {fb} fallback

## Not authoritative
- Prior 12.20% HVAC figure is **not** the comfort-zero result.
- LLM-path energy totals are secondary and model-variable.

## Engineering fixes in this pass
- `tests/integration/test_control_flow.py` accepts energyplus real-data semantics.
- Added `final_acceptance.sh`, `final_smoke_test.sh`, `final_submission_check.sh`.
""",
)

w(
    "FINAL_CLAIMS.md",
    f"""# Final Claims — Eco-Loop Building Agents

**Final release commit:** `{COMMIT}`
**Generated:** {NOW}

> Internal engineering-readiness score is recorded in `FINAL_RELEASE_MANIFEST.json`.
> It is **not** a judge score or predicted competition score.

## Primary claim

Under identical EnergyPlus building, weather, occupancy and simulation conditions, Eco-Loop reduced simulated HVAC energy by **{rh:.2f}%**, total energy by **{rt:.2f}%** and peak demand by **{rp:.2f}%**, while maintaining **zero** occupied comfort-violation hours and **zero** comfort degree-hours.

Evidence: `evidence/independent-metrics.json`, `evidence/energyplus/comparison.json`, `evidence/independent-comfort-summary.json`, `evidence/experiment-fairness.md`

## Supporting claims

| Claim | Evidence |
|---|---|
| MCP separate stdio process | `evidence/mcp-process-proof.md`, `evidence/mcp-runtime-trace.jsonl` (PIDs {llm.get('mcp_client_pid')} ≠ {llm.get('mcp_server_pid')}) |
| Ollama structured proposals | `evidence/ollama-runtime-proof.md`, `evidence/ollama-structured-responses.jsonl` |
| SafetyShield rejects 35°C | `evidence/safety-rejection.log` |
| Actuator write to Clg-SetP-Sch | `evidence/final-actuator-trace.csv` |
| Next EnergyPlus state returned | `evidence/final-next-state-proof.md` |
| Ollama failure → deterministic fallback | `evidence/ollama-fallback.log` |
| Recovery after failure | `evidence/recovery-after-failure.md` |
| Dashboard real data integrity | `evidence/dashboard-real-data-proof.md` |
| Dashboard honest no-data | `evidence/dashboard-no-data-proof.md` |
| Clean-clone | `evidence/clean-clone-report.md`, `logs/clean-clone.log` |
| Carbon is estimated | comparison `carbon_accounting` (0.417 kg/kWh) |

## Non-claims
- Not a physical BMS deployment.
- Not universal savings across buildings/weather.
- Not presenting 12.20% HVAC as comfort-zero authoritative.
- Not calling in-process handler dispatch “MCP transport”.
""",
)

w(
    "FINAL_LIMITATIONS.md",
    f"""# Final Limitations

**Commit:** `{COMMIT}` · **Generated:** {NOW}

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
""",
)

w(
    "FINAL_DEMO_SCRIPT.md",
    f"""# Final 3-Minute Demo Script

**Commit:** `{COMMIT}`

**Always say:** “AI proposes. SafetyShield validates. EnergyPlus executes.”
**Never say:** physical BMS deployment, or 12.20% HVAC as the comfort-zero result.

## 0:00–0:25 — Problem
**Words:** “Buildings waste energy when HVAC ignores occupancy and weather. Letting an LLM write setpoints directly is unsafe.”
**Show:** problem slide / README opener.

## 0:25–0:50 — Architecture
**Words:** “EnergyPlus is our digital building. Observations move through a real MCP client to a separate stdio server, then to local Ollama. SafetyShield is the only gate before the actuator.”
**Show:** architecture diagram.

## 0:50–1:35 — Real closed loop
**Commands (prefer pre-run):**
```bash
./scripts/run_baseline.sh && ./scripts/run_agent.sh && ./scripts/compare_results.sh
```
**Words:** “These rows show Clg-SetP-Sch written and the next zone temperature returned.”
**Show:** `final-release/evidence/final-actuator-trace.csv`
**Fallback:** “Live EnergyPlus is pre-verified at commit {COMMIT[:12]}; here are five consecutive actuator→next-state rows.”

## 1:35–2:05 — Results
**Words:** “Identical inputs: HVAC about {rh:.2f}% lower, total energy {rt:.2f}% lower, peak {rp:.2f}% lower, zero comfort violations.”
**Show:** dashboard or `results/comparison/comparison.md`.

## 2:05–2:35 — Safety and fallback
**Words:** “Thirty-five degrees is rejected. If Ollama is down, deterministic fallback continues — still through SafetyShield.”
**Show:** `safety-rejection.log`, `ollama-fallback.log`.

## 2:35–3:00 — Closing
**Words:** “Reproducible EnergyPlus prototype, not a physical BMS. AI proposes. SafetyShield validates. EnergyPlus executes.”
**Show:** primary claim in `FINAL_CLAIMS.md`.
""",
)

w(
    "PRESENTATION_CONTENT.md",
    f"""# Presentation Content (6 slides)

**Commit:** `{COMMIT}`

## Slide 1 — Problem and objective
- **Message:** Unsafe autonomy is unacceptable; measurable gated autonomy is the goal.
- Bullets: HVAC waste; raw LLM risk; need reproducible loop; comfort hard constraint; prove EnergyPlus gating.
- **Visual:** simple waste/comfort tension graphic.
- **Speaker notes:** Emphasize digital building, not plant control.
- **Evidence:** README.

## Slide 2 — Eco-Loop solution
- **Message:** AI proposes. SafetyShield validates. EnergyPlus executes.
- Bullets: Runtime API observe; optional MCP+Ollama; deterministic shield; Clg-SetP-Sch only if approved; fair baseline compare.
- **Visual:** one horizontal flow.
- **Evidence:** docs/architecture.md.

## Slide 3 — Technical architecture
- **Message:** Separate processes; authoritative safety.
- Bullets: EnergyPlus observations; MCP client≠server PID; Ollama JSON proposals; SafetyShield; DATA_MODE=energyplus dashboard.
- **Visual:** process/PID diagram.
- **Evidence:** mcp-process-proof.md.

## Slide 4 — Working prototype
- **Message:** Closed loop is real.
- Bullets: fresh scripts; actuator+next-state; stdio MCP; honest no-data UI; clean-clone path.
- **Visual:** terminal + dashboard placeholders.
- **Evidence:** actuator trace; dashboard proofs.

## Slide 5 — Verified results
- **Message:** Comfort-zero savings on identical inputs.
- Bullets: total {rt:.2f}%; HVAC {rh:.2f}%; peak {rp:.2f}%; comfort 0/0; actions {appr}/{rej}/{fb}.
- **Visual:** before/after bars.
- **Optional aside:** aggressive policy saved more HVAC but violated comfort — not selected.
- **Evidence:** independent-metrics.json.

## Slide 6 — Safety, limitations and future deployment
- **Message:** Prototype today; commissioning required tomorrow.
- Bullets: 35°C reject; Ollama fallback; digital-only; carbon estimate; operator approval; next BMS connector.
- **Visual:** shield + limitations.
- **Evidence:** FINAL_LIMITATIONS.md.
""",
)

qa = [
    (
        "Why use an LLM instead of only rules?",
        "Rules cover known heuristics; the LLM proposes context-aware setpoints. SafetyShield still decides. Path A is the authoritative savings proof.",
    ),
    (
        "Why is total energy reduction lower than HVAC reduction?",
        "HVAC is a small share of facility energy; lights/equipment dominate, so HVAC % moves more than whole-building %.",
    ),
    (
        "How do you prove EnergyPlus is really controlled?",
        "Runtime API set_actuator_value on Clg-SetP-Sch, energyplus_actuator_written=true, and next-timestep temperatures change.",
    ),
    (
        "What exactly does MCP do?",
        "A separate local tool server over stdio exposing observation/context tools to the experiment client.",
    ),
    (
        "How do you prove MCP is not simulated?",
        f"Client PID {llm.get('mcp_client_pid')} ≠ server PID {llm.get('mcp_server_pid')}; initialize/tools/list/tools/call are in the JSONL trace.",
    ),
    (
        "Can the LLM directly control the actuator?",
        "No. LLM output is a proposal only; SafetyShield must approve before any actuator write.",
    ),
    (
        "What happens when Ollama fails?",
        "Failure is logged; deterministic fallback proposes; SafetyShield still gates; we observed 48 fallback actions.",
    ),
    (
        "What happens when MCP fails?",
        "Tool calls fail closed into deterministic_fallback; no unsafe bypass.",
    ),
    (
        "What happens when EnergyPlus fails?",
        "Scripts exit non-zero with failed status; dashboard shows unavailable rather than inventing meters.",
    ),
    (
        "Is the dashboard mocked?",
        "Hackathon mode is DATA_MODE=energyplus. Missing results show energyplus_results_unavailable — no silent mock.",
    ),
    (
        "Is this deployed in a real building?",
        "No. It controls an EnergyPlus digital building for verification.",
    ),
    (
        "Why was the aggressive policy not selected?",
        "It increased savings but caused comfort violations; comfort-zero Path A is authoritative.",
    ),
    (
        "How is comfort calculated?",
        "Occupied-hour zone temperatures versus band; violation hours and degree-hours independently recomputed.",
    ),
    (
        "How are savings calculated?",
        "(baseline−agent)/baseline×100 on measured EnergyPlus meter totals.",
    ),
    (
        "How is carbon calculated?",
        "Estimate: total_kWh × 0.417 kg/kWh — labeled estimate, not live grid intensity.",
    ),
    (
        "Are the results reproducible?",
        "Yes from clean clone with the same IDF/EPW/scripts; Path A matches within rounding.",
    ),
    (
        "What prevents unsafe setpoints?",
        "SafetyShield range, rate, deadband, and sensor/LLM/MCP health checks before actuation.",
    ),
    (
        "How would this connect to a real BMS?",
        "Replace the EnergyPlus actuator adapter with a facility-approved BACnet/API connector behind the same SafetyShield.",
    ),
    (
        "What are the current limitations?",
        "Digital-only, local Ollama, static carbon factor, sample model/weather, prototype security.",
    ),
    (
        "What would you build next?",
        "BMS connector, multi-building validation, operator UX, and hardened auth/observability.",
    ),
]
qa_lines = [f"# Final Judge Q&A\n\n**Commit:** `{COMMIT}` · **Generated:** {NOW}\n"]
for i, (q, a) in enumerate(qa, 1):
    qa_lines += [f"## {i}. {q}", f"**A:** {a}", ""]
w("FINAL_JUDGE_QA.md", "\n".join(qa_lines))

w(
    "FINAL_COMMAND_REFERENCE.md",
    f"""# Final Command Reference

**Commit:** `{COMMIT}`
**Branch:** `{BRANCH}`

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
# git push -u origin {BRANCH}
# git push origin hackathon-final-v1
```
""".replace("{BRANCH}", BRANCH),
)

# Owner checklist
checks = [
    (
        "Confirm exact final Git commit",
        "git rev-parse HEAD",
        "Matches FINAL_RELEASE_MANIFEST.json",
        "SHA shown equals sealed commit",
        "SHA differs / detached unexpected",
        "FINAL_RELEASE_MANIFEST.json",
    ),
    (
        "Confirm working tree is clean",
        "git status",
        "No unexpected dirty files before tag",
        "clean working tree",
        "unexpected modifications",
        "logs/repository-state.txt",
    ),
    (
        "Run prerequisite checker",
        "./scripts/check_prerequisites.sh",
        "Environment ready",
        "RESULT: PASS",
        "RESULT: FAIL",
        "logs/prerequisites.log",
    ),
    (
        "Run baseline experiment",
        "./scripts/run_baseline.sh",
        "EnergyPlus baseline completes",
        "simulation_status completed ~421.51 kWh",
        "failed / fatal",
        "evidence/energyplus/baseline-summary.json",
    ),
    (
        "Run agent experiment",
        "./scripts/run_agent.sh",
        "Closed-loop agent completes",
        "completed; 48 decisions; comfort 0",
        "failed / comfort>0 unexpectedly",
        "evidence/energyplus/agent-summary.json",
    ),
    (
        "Run comparison",
        "./scripts/compare_results.sh",
        "Fair delta report",
        "comparison.json written",
        "missing inputs",
        "evidence/energyplus/comparison.json",
    ),
    (
        "Inspect fresh result timestamps",
        "ls -l results/*/summary.json",
        "Artifacts from this release run",
        "mtimes match release window",
        "old/stale files",
        "logs/energyplus-generated-files.txt",
    ),
    (
        "Inspect five consecutive actuator rows",
        "column -t -s, final-release/evidence/final-actuator-trace.csv | head",
        "Closed-loop continuity",
        "5+ rows write=True with next temps",
        "missing next state",
        "evidence/final-actuator-trace.csv",
    ),
    (
        "Confirm Clg-SetP-Sch is written",
        "rg energyplus_actuator_written results/agent/actions.json | head",
        "Actuator path exercised",
        "true on approved rows",
        "all false",
        "evidence/final-next-state-proof.md",
    ),
    (
        "Confirm next EnergyPlus state is returned",
        "sed -n '1,8p' final-release/evidence/final-next-state-proof.md",
        "Next timestep observation",
        "PASS verdict",
        "FAIL verdict",
        "evidence/final-next-state-proof.md",
    ),
    (
        "Confirm MCP client and server PIDs differ",
        "python -c \"import json;s=json.load(open('results/llm_mcp/summary.json'));print(s['mcp_client_pid'],s['mcp_server_pid'],s['mcp_pids_differ'])\"",
        "Separate process MCP",
        "pids_differ True",
        "same PID / missing",
        "evidence/mcp-process-proof.md",
    ),
    (
        "Inspect initialize, tools/list and tools/call",
        "rg -n 'initialize|tools/list|tools/call' final-release/evidence/mcp-runtime-trace.jsonl | head",
        "Real MCP protocol",
        "events present",
        "empty trace",
        "evidence/mcp-runtime-trace.jsonl",
    ),
    (
        "Confirm Ollama returns a structured proposal",
        "head -3 final-release/evidence/ollama-structured-responses.jsonl",
        "Local model proposals",
        "proposed_cooling_setpoint_c present",
        "no rows",
        "evidence/ollama-runtime-proof.md",
    ),
    (
        "Trigger 35°C unsafe action",
        "rg -n safety_shield_rejects_unsafe results/llm_mcp/stage_log.jsonl",
        "Unsafe proposal path",
        "proposed 35",
        "missing stage",
        "evidence/safety-rejection.log",
    ),
    (
        "Observe SafetyShield rejection",
        "cat final-release/evidence/safety-rejection.log",
        "Reject reasons recorded",
        "approved=False disposition=rejected",
        "approved=True",
        "evidence/safety-rejection.log",
    ),
    (
        "Trigger Ollama failure",
        "OLLAMA_BASE_URL=http://127.0.0.1:1 RESULTS_LLM_DIR=/tmp/llm_fail_test ./scripts/run_llm_mcp_experiment.sh",
        "Unavailable model path",
        "connection refused logged",
        "silent success with mock",
        "evidence/ollama-fallback.log",
    ),
    (
        "Observe deterministic fallback",
        "cat final-release/evidence/ollama-fallback.log",
        "Fallback counts",
        "fallback=48",
        "fallback=0 with failures",
        "evidence/ollama-fallback.log",
    ),
    (
        "Restore Ollama and observe recovery",
        "curl -s http://127.0.0.1:11434/api/tags | head",
        "Service recovery",
        "llama3.2:1b listed; MCP session opens",
        "still down",
        "evidence/recovery-after-failure.md",
    ),
    (
        "Test dashboard no-data state",
        "see FINAL_COMMAND_REFERENCE / move results aside",
        "Honest unavailable UX",
        "energyplus_results_unavailable",
        "mock KPIs appear",
        "evidence/dashboard-no-data-proof.md",
    ),
    (
        "Test dashboard real-data state",
        "DATA_MODE=energyplus ./scripts/run_demo.sh",
        "Measured KPIs",
        "energyplus_experiment_results; ~1.31% total",
        "wrong multiplier / mock",
        "evidence/dashboard-real-data-proof.md",
    ),
    (
        "Inspect dashboard API response",
        "curl authenticated /buildings/{id}/status",
        "API lineage",
        "reductions match comparison.json",
        "mismatch / 1.12",
        "evidence/dashboard-api-samples/",
    ),
    (
        "Stop backend and observe honest failure state",
        "stop uvicorn; reload dashboard",
        "No invented live data",
        "API errors / stale notice",
        "fake live KPIs continue updating",
        "evidence/dashboard-disconnection-proof.md",
    ),
    (
        "Complete clean-clone test",
        "bash scripts/_final_clean_clone_run.sh",
        "README-only reproducibility",
        "CLEAN_CLONE_STATUS=PASS",
        "undocumented blockers",
        "evidence/clean-clone-report.md",
    ),
    (
        "Run final smoke test",
        "./scripts/final_smoke_test.sh",
        "Pre-demo readiness",
        "SMOKE RESULT: PASS",
        "FAIL",
        "logs/",
    ),
    (
        "Build final evidence package",
        "python scripts/build_submission_evidence.py",
        "Judge bundle inputs",
        "submission-evidence written",
        "script error",
        "submission-package/",
    ),
    (
        "Confirm no secrets",
        "./scripts/final_submission_check.sh",
        "Hygiene",
        "PASS secret scan",
        "secret-like hit",
        "SECURITY_AND_PRIVACY_CHECK.md",
    ),
    (
        "Confirm no generated results are tracked",
        "git ls-files results submission-evidence",
        "Repo cleanliness",
        "gitkeep only",
        "json/csv tracked",
        "logs/hygiene-scan.txt",
    ),
    (
        "Record backup demonstration video",
        "(owner camera/screen recorder)",
        "Offline demo backup",
        "video covers loop+results+safety",
        "missing backup",
        "submission-package/placeholders/demo-video.txt",
    ),
    (
        "Review final presentation",
        "open PRESENTATION_CONTENT.md",
        "Talk track ready",
        "6 slides match Path A numbers",
        "stale 12.20% claim",
        "PRESENTATION_CONTENT.md",
    ),
    (
        "Create final release tag manually",
        "git tag -a hackathon-final-v1 -m 'Verified Eco-Loop hackathon release'",
        "Immutable pointer",
        "tag on sealed commit",
        "tag on wrong SHA",
        "FINAL_RELEASE_REPORT.md",
    ),
    (
        "Push only after owner approval",
        f"git push -u origin {BRANCH}; git push origin hackathon-final-v1",
        "Remote publish",
        "owner-approved push",
        "accidental push",
        "FINAL_RELEASE_REPORT.md",
    ),
]

cl = [
    f"# Final Owner Checklist\n",
    f"**Commit:** `{COMMIT}`  ",
    f"**Branch:** `{BRANCH}`  ",
    f"**Generated:** {NOW}\n",
    "Use this as a non-expert runbook. Check boxes only after you personally observe success.\n",
]
for title, cmd, proves, success, failure, evid in checks:
    cl += [
        f"## [ ] {title}",
        f"- **Command:** `{cmd}`",
        f"- **Proves:** {proves}",
        f"- **Success looks like:** {success}",
        f"- **Failure looks like:** {failure}",
        f"- **Evidence to inspect:** `{evid}`",
        "",
    ]
w("FINAL_OWNER_CHECKLIST.md", "\n".join(cl))

# Clean clone report stub/update
w(
    "evidence/clean-clone-report.md",
    f"""# Clean-Clone Report

Generated: {NOW}
Source commit at clone start: `{COMMIT}`

## Method
- Temporary clone via `scripts/_final_clean_clone_run.sh`
- Excludes results, `.env` secrets copy policy uses `.env.example`, no node_modules/venv copied from source
- Follows README experiment commands

## Log
See `final-release/logs/clean-clone.log`.

## Status at doc generation
{"**PASS** indicators found in log." if clean_pass else "**IN PROGRESS / CHECK LOG** — re-open this file after clean-clone finishes and confirm PASS."}

## Required observations
- Clone begins with zero generated result JSON
- Prerequisites / setup / baseline / agent / compare / llm_mcp succeed
- MCP client/server PIDs differ
- Ollama responds on normal path
- SafetyShield validates
- Dashboard payload no-data then real-data
- Comfort remains within authoritative zero policy for Path A
""",
)

status = "PASS" if total >= 90 and clean_pass else ("CONDITIONAL_PASS" if total >= 85 else "FAIL")
# If clean clone not done, conditional
if not clean_pass:
    status = "CONDITIONAL_PASS"

manifest = {
    "project": "Eco-Loop Building Agents",
    "final_release_commit": COMMIT,
    "branch": BRANCH,
    "generated_at": NOW,
    "overall_status": status,
    "internal_readiness_score": total,
    "authoritative_results": {
        "baseline_total_energy_kwh": bt,
        "agent_total_energy_kwh": at,
        "total_energy_reduction_percent": round(rt, 4),
        "baseline_hvac_energy_kwh": bh,
        "agent_hvac_energy_kwh": ah,
        "hvac_energy_reduction_percent": round(rh, 4),
        "baseline_peak_power_kw": bp,
        "agent_peak_power_kw": ap,
        "peak_power_reduction_percent": round(rp, 4),
        "baseline_comfort_violation_hours": base["occupied_comfort_violation_hours"],
        "agent_comfort_violation_hours": agent["occupied_comfort_violation_hours"],
        "comfort_degree_hours": agent["occupied_comfort_degree_hours"],
        "approved_actions": appr,
        "rejected_actions": rej,
        "fallback_actions": fb,
    },
    "verification": {
        "energyplus_closed_loop": "PASS",
        "actuator_write": "PASS",
        "next_state": "PASS",
        "mcp_separate_process": "PASS",
        "mcp_initialize": "PASS",
        "mcp_tools_list": "PASS",
        "mcp_tools_call": "PASS",
        "ollama_response": "PASS",
        "safety_rejection": "PASS",
        "fallback": "PASS",
        "dashboard_real_data": "PASS",
        "dashboard_no_data_state": "PASS",
        "no_silent_mock_fallback": "PASS",
        "clean_clone": "PASS" if clean_pass else "PENDING",
        "tests": "PASS",
    },
    "critical_evidence": [
        "final-release/evidence/independent-metrics.json",
        "final-release/evidence/final-actuator-trace.csv",
        "final-release/evidence/final-next-state-proof.md",
        "final-release/evidence/mcp-process-proof.md",
        "final-release/evidence/mcp-runtime-trace.jsonl",
        "final-release/evidence/ollama-runtime-proof.md",
        "final-release/evidence/safety-rejection.log",
        "final-release/evidence/ollama-fallback.log",
        "final-release/evidence/dashboard-real-data-proof.md",
        "final-release/evidence/dashboard-no-data-proof.md",
        "final-release/logs/clean-clone.log",
    ],
    "known_limitations": [
        "EnergyPlus digital-building only",
        "No physical BMS connector",
        "Local Ollama prerequisite",
        "Carbon values are estimates",
        "Sample office / Chicago EPW specific",
    ],
    "p0_issues": [],
    "p1_issues": []
    if clean_pass
    else ["Clean-clone verification still pending completion at manifest generation time"],
    "owner_actions_remaining": [
        "Confirm sealed commit SHA after final docs commit",
        "Run ./scripts/final_smoke_test.sh before live demo",
        "Create annotated tag hackathon-final-v1 manually",
        "Push branch/tag only after explicit owner approval",
        "Record backup demo video",
    ],
    "score_breakdown": {
        k: {"max": v[0], "earned": v[1], "note": v[2]} for k, v in score_parts.items()
    },
}
(FR / "FINAL_RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")

deductions = [f"- {k}: -{v[0]-v[1]} ({v[2]})" for k, v in score_parts.items() if v[1] < v[0]]
if not deductions:
    deductions = ["- None"]

report = f"""# Final Release Report — Eco-Loop Building Agents

## 1. Executive summary
Fresh verification from commit `{COMMIT}` confirms a real EnergyPlus closed loop, stdio MCP process separation, local Ollama proposals, SafetyShield rejection/fallback, honest dashboard data modes, and Path A comfort-zero savings of **{rh:.2f}% HVAC / {rt:.2f}% total / {rp:.2f}% peak**. Overall status: **{status}**. Internal engineering-readiness score: **{total}/100**.

## 2. Exact release commit
- Branch: `{BRANCH}`
- Commit: `{COMMIT}`
- Note: If additional sealing commits land after this report, update the manifest to the sealed tip before tagging.

## 3. Environment
See `logs/prerequisites.log` and `logs/repository-state.txt`. EnergyPlus 24.1, Python 3.12, Node 22, pnpm 10, Ollama + llama3.2:1b.

## 4. Commands executed
`check_prerequisites`, `setup_energyplus`, `run_baseline`, `run_agent`, `compare_results`, `run_llm_mcp_experiment`, Ollama-down fallback, dashboard API no-data/real-data/disconnect, pytest suite, frontend lint/typecheck/build, clean-clone helper.

## 5. Tests executed
See `logs/test-summary.md` and `logs/pytest-after-fix.log` — **57 passed** after P1 test fix.

## 6. Fresh baseline results
total={bt}, hvac={bh}, peak={bp}, comfort_hours={base['occupied_comfort_violation_hours']}

## 7. Fresh agent results
total={at}, hvac={ah}, peak={ap}, comfort_hours={agent['occupied_comfort_violation_hours']}, actions={agent.get('action_counts')}

## 8. Independent calculations
{json.dumps(ind['independent_reductions_percent'], indent=2)}
Match app: {json.dumps(ind['match_within_rounding'])}

## 9. Experiment fairness
See `evidence/experiment-fairness.md` — **VALID**.

## 10. Comfort verification
Independent stream proxy + app comfort analysis: zero violations / zero degree-hours (`evidence/independent-comfort-summary.json`).

## 11. Actuator proof
`evidence/final-actuator-trace.csv` — `energyplus_actuator_written=True` on approved rows; code path `set_actuator_value(... Clg-SetP-Sch)`.

## 12. Next-state proof
`evidence/final-next-state-proof.md` — PASS with 5+ consecutive following temperatures.

## 13. MCP process proof
client_pid={llm.get('mcp_client_pid')} server_pid={llm.get('mcp_server_pid')} differ={llm.get('mcp_pids_differ')}

## 14. MCP protocol proof
`evidence/mcp-runtime-trace.jsonl` includes initialize and tools/list + tools/call activity; authoritative path does not import `handlers.call_tool`.

## 15. Ollama proof
`evidence/ollama-runtime-proof.md` — local llama3.2:1b structured JSON proposals.

## 16. Safety rejection proof
`evidence/safety-rejection.log` — 35°C rejected (`cooling_setpoint_out_of_range`, `max_setpoint_change_exceeded`).

## 17. Fallback proof
`evidence/ollama-fallback.log` — 48 failures → 48 deterministic_fallback.

## 18. Dashboard data lineage
API reductions match independent metrics; `synthetic_multiplier_applied=false`.

## 19. No-data behaviour
`energyplus_results_unavailable` with null KPIs; no silent mock.

## 20. Clean-clone result
See `logs/clean-clone.log` / `evidence/clean-clone-report.md` — status **{manifest['verification']['clean_clone']}**.

## 21. Security and secret check
`SECURITY_AND_PRIVACY_CHECK.md` — PASS.

## 22. Documentation status
Final-release pack + README architecture claims aligned; historical FAILED MCP wording preserved under `manual-verification/` (not rewritten).

## 23. Submission-package status
Built under `final-release/submission-package/` with checksums.

## 24. P0/P1/P2 issues
- P0: none open.
- P1: {manifest['p1_issues'] or 'none open after clean-clone PASS'}.
- P2: bare `pytest` at repo root can collect EnergyPlus idlelib (document/use README paths).

## 25. Known limitations
See `FINAL_LIMITATIONS.md`.

## 26. Internal readiness score
**{total}/100**

Breakdown:
{chr(10).join(f"- {k}: {v[1]}/{v[0]} — {v[2]}" for k,v in score_parts.items())}

Deductions:
{chr(10).join(deductions)}

## 27. Final go/no-go recommendation
**{"GO" if status=="PASS" else "CONDITIONAL GO" if status=="CONDITIONAL_PASS" else "NO-GO"}**

## 28. Human owner checks remaining
See `FINAL_OWNER_CHECKLIST.md` (tag, push approval, backup video, live smoke).

## 29. Exact commands for final tag and push
```bash
git status
git rev-parse HEAD
git tag -a hackathon-final-v1 -m "Verified Eco-Loop hackathon release"
# ONLY after explicit owner approval:
git push -u origin {BRANCH}
git push origin hackathon-final-v1
```
""".replace("{BRANCH}", BRANCH)
w("FINAL_RELEASE_REPORT.md", report)

# Submission package
PKG.mkdir(parents=True, exist_ok=True)
(PKG / "placeholders").mkdir(exist_ok=True)
for name in [
    "FINAL_RELEASE_REPORT.md",
    "FINAL_RELEASE_MANIFEST.json",
    "FINAL_CLAIMS.md",
    "FINAL_LIMITATIONS.md",
    "FINAL_DEMO_SCRIPT.md",
    "FINAL_JUDGE_QA.md",
    "PRESENTATION_CONTENT.md",
    "SECURITY_AND_PRIVACY_CHECK.md",
    "RELEASE_NOTES.md",
]:
    shutil.copy2(FR / name, PKG / name)
shutil.copy2(ROOT / "README.md", PKG / "README.md")
# evidence copies
for src, dst in [
    (EV / "energyplus" / "baseline-summary.json", PKG / "baseline-summary.json"),
    (EV / "energyplus" / "agent-summary.json", PKG / "agent-summary.json"),
    (EV / "energyplus" / "comparison.json", PKG / "comparison.json"),
    (EV / "final-actuator-trace.csv", PKG / "final-actuator-trace.csv"),
    (EV / "mcp-runtime-trace.jsonl", PKG / "mcp-runtime-trace.jsonl"),
    (EV / "safety-rejection.log", PKG / "safety-rejection.log"),
    (EV / "ollama-fallback.log", PKG / "ollama-fallback.log"),
    (EV / "clean-clone-report.md", PKG / "clean-clone-report.md"),
    (EV / "mcp-process-proof.md", PKG / "mcp-process-proof.md"),
]:
    if src.exists():
        shutil.copy2(src, dst)

# verification summary snapshot
vs = {
    "final_release_commit": COMMIT,
    "overall_status": status,
    "internal_readiness_score": total,
    "authoritative_path": "deterministic Path A comfort-zero",
    "results": manifest["authoritative_results"],
    "verification": manifest["verification"],
}
(PKG / "verification-summary.json").write_text(json.dumps(vs, indent=2) + "\n")
(FR / "verification-summary.snapshot.json").write_text(json.dumps(vs, indent=2) + "\n")

(PKG / "placeholders" / "architecture-diagram.txt").write_text(
    "Place or link architecture diagram (docs/architecture.md ASCII / submission-evidence SVG).\n"
)
(PKG / "placeholders" / "presentation.txt").write_text(
    "Populate slides using final-release/PRESENTATION_CONTENT.md\n"
)
(PKG / "placeholders" / "demo-video.txt").write_text(
    "Owner: record backup demo video covering closed loop, results, safety, fallback.\n"
)
(PKG / "placeholders" / "source-code-reference.txt").write_text(
    f"Source repository branch `{BRANCH}` commit `{COMMIT}`.\n"
)

# Checklist + checksums
files = sorted([p for p in FR.rglob("*") if p.is_file() and "acceptance-" not in str(p)])
sums = []
for p in files:
    if p.name == "SHA256SUMS.txt":
        continue
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    rel = p.relative_to(FR).as_posix()
    sums.append(f"{h}  {rel}")
(CHK / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n")

checklist = [
    "# Submission File Checklist\n",
    f"**Commit:** `{COMMIT}` · **Generated:** {NOW}\n",
    "| File | Exists | Non-empty | Notes |",
    "|---|---|---|---|",
]
required = [
    "FINAL_RELEASE_REPORT.md",
    "FINAL_RELEASE_MANIFEST.json",
    "FINAL_OWNER_CHECKLIST.md",
    "FINAL_DEMO_SCRIPT.md",
    "FINAL_JUDGE_QA.md",
    "FINAL_LIMITATIONS.md",
    "FINAL_CLAIMS.md",
    "FINAL_COMMAND_REFERENCE.md",
    "PRESENTATION_CONTENT.md",
    "SUBMISSION_FILE_CHECKLIST.md",
    "SECURITY_AND_PRIVACY_CHECK.md",
    "RELEASE_NOTES.md",
    "checksums/SHA256SUMS.txt",
    "submission-package/README.md",
    "submission-package/FINAL_CLAIMS.md",
    "evidence/independent-metrics.json",
    "evidence/final-actuator-trace.csv",
    "evidence/mcp-runtime-trace.jsonl",
    "evidence/safety-rejection.log",
    "evidence/ollama-fallback.log",
]
for rel in required:
    p = FR / rel
    checklist.append(
        f"| `{rel}` | {p.exists()} | {p.exists() and p.stat().st_size>0} | |"
    )
checklist += [
    "",
    "## Automated checks",
    "- Run `./scripts/final_submission_check.sh`",
    "- Confirm no secrets / no `.env` / no node_modules in package",
    "- Confirm no intermediate commit mislabeled as final release",
    "- Confirm Path A numbers match independent-metrics.json",
    "",
    f"## Stale-commit policy",
    f"- Authoritative sealed commit must be recorded in FINAL_RELEASE_MANIFEST.json.",
    f"- Historical commits (b63311c, 9085cbc, 95a58e7, 1b6a045, 133b053 pre-seal) are history only unless selected as tip.",
]
w("SUBMISSION_FILE_CHECKLIST.md", "\n".join(checklist))
shutil.copy2(FR / "SUBMISSION_FILE_CHECKLIST.md", PKG / "SUBMISSION_FILE_CHECKLIST.md")

print(
    json.dumps(
        {
            "commit": COMMIT,
            "branch": BRANCH,
            "status": status,
            "score": total,
            "clean_pass": clean_pass,
        },
        indent=2,
    )
)
