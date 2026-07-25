#!/usr/bin/env bash
# Compare baseline vs agent EnergyPlus experiment summaries (machine-readable).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

BASELINE_JSON="${1:-$ROOT/results/baseline/summary.json}"
AGENT_JSON="${2:-$ROOT/results/agent/summary.json}"
OUT_DIR="${RESULTS_COMPARISON_DIR:-$ROOT/results/comparison}"
mkdir -p "$OUT_DIR"

PYTHON="${PYTHON:-$ROOT/.venv/bin/python}"
if [[ ! -x "$PYTHON" ]]; then
  PYTHON="$(command -v python3)"
fi

export PYTHONPATH="$ROOT/services/simulator:$ROOT/services/optimizer:${PYTHONPATH:-}"

if [[ ! -f "$BASELINE_JSON" ]]; then
  echo "ERROR: missing baseline summary: $BASELINE_JSON (run ./scripts/run_baseline.sh)" >&2
  exit 2
fi
if [[ ! -f "$AGENT_JSON" ]]; then
  echo "ERROR: missing agent summary: $AGENT_JSON (run ./scripts/run_agent.sh)" >&2
  exit 2
fi

"$PYTHON" - <<PY
import json, sys
from pathlib import Path
from twinpilot_simulator.ep_experiment import compare_summaries

baseline = json.loads(Path("$BASELINE_JSON").read_text())
agent = json.loads(Path("$AGENT_JSON").read_text())
if baseline.get("simulation_status") != "completed":
    print("ERROR: baseline simulation_status != completed", file=sys.stderr)
    sys.exit(1)
if agent.get("simulation_status") != "completed":
    print("ERROR: agent simulation_status != completed", file=sys.stderr)
    sys.exit(1)

cmp = compare_summaries(baseline, agent)
out = Path("$OUT_DIR")
(out / "comparison.json").write_text(json.dumps(cmp, indent=2))
md = []
md.append("# Baseline vs Agent Comparison")
md.append("")
md.append(f"- Generated: `{cmp['timestamp_utc']}`")
md.append(f"- Inputs identical: **{cmp['inputs_identical']}**")
md.append("")
md.append("| Metric | Baseline | Agent | Δ (agent−baseline) | % |")
md.append("|--------|----------|-------|--------------------|---|")
for key, label in [
    ("total_energy_kwh", "Total energy (kWh)"),
    ("hvac_energy_kwh", "HVAC energy (kWh)"),
    ("peak_power_kw", "Peak power (kW)"),
    ("carbon_estimate_kg", "Carbon estimate (kg)"),
    ("occupied_comfort_violation_hours", "Occupied comfort violation hours"),
]:
    d = cmp[key]
    pct = d.get("percent_reduction")
    if pct is None:
        pct = "n/a" if d.get("percent_delta") is None else f"{d['percent_delta']}%"
    else:
        pct = f"{pct}%"
    md.append(
        f"| {label} | {d['baseline']} | {d['agent']} | {d['absolute_delta_agent_minus_baseline']} | {pct} |"
    )
md.append("")
md.append("## Agent actions")
md.append(f"```json\n{json.dumps(cmp.get('agent_action_counts'), indent=2)}\n```")
md.append("")
md.append("## Notes")
for n in cmp["notes"]:
    md.append(f"- {n}")
(out / "comparison.md").write_text("\n".join(md) + "\n")
print(json.dumps(cmp, indent=2))
print(f"Wrote {out / 'comparison.json'}")
print(f"Wrote {out / 'comparison.md'}")
PY
