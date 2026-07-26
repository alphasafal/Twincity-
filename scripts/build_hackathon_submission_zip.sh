#!/usr/bin/env bash
# Build Eco-Loop-Hackathon-Submission.zip (no secrets, no node_modules, no .env).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUT_DIR="${1:-$ROOT/Eco-Loop-Hackathon-Submission}"
ZIP_PATH="${2:-$ROOT/Eco-Loop-Hackathon-Submission.zip}"
rm -rf "$OUT_DIR" "$ZIP_PATH"
mkdir -p "$OUT_DIR"/{building-models,results,evidence,docs}

# Markdown + rendered deliverables
cp -f "$ROOT/README.md" "$OUT_DIR/README.md"
cp -f "$ROOT/final-release/PRESENTATION_CONTENT.md" "$OUT_DIR/Eco-Loop-Presentation.md"
# Official IDEA PDF (single copy to keep ZIP small)
if [[ -f "$ROOT/final-release/presentation/Eco-Loop_Building_Agents.pdf" ]]; then
  cp -f "$ROOT/final-release/presentation/Eco-Loop_Building_Agents.pdf" "$OUT_DIR/Eco-Loop_Building_Agents.pdf"
elif [[ -f "$ROOT/final-release/presentation/Eco-Loop-Presentation.pdf" ]]; then
  cp -f "$ROOT/final-release/presentation/Eco-Loop-Presentation.pdf" "$OUT_DIR/Eco-Loop_Building_Agents.pdf"
fi
cp -f "$ROOT/docs/architecture.md" "$OUT_DIR/Architecture-Document.md" 2>/dev/null || \
  cp -f "$ROOT/final-release/FINAL_RELEASE_REPORT.md" "$OUT_DIR/Architecture-Document.md"
if [[ -f "$ROOT/final-release/presentation/Architecture-Document.pdf" ]]; then
  cp -f "$ROOT/final-release/presentation/Architecture-Document.pdf" "$OUT_DIR/Architecture-Document.pdf"
fi
if [[ -f "$ROOT/final-release/presentation/IDEA_KEY_PASTE_GUIDE.md" ]]; then
  cp -f "$ROOT/final-release/presentation/IDEA_KEY_PASTE_GUIDE.md" "$OUT_DIR/IDEA_KEY_PASTE_GUIDE.md"
fi
if [[ -f "$ROOT/final-release/IDEA_PPT_6_SLIDES.md" ]]; then
  cp -f "$ROOT/final-release/IDEA_PPT_6_SLIDES.md" "$OUT_DIR/IDEA_PPT_6_SLIDES.md"
fi
if [[ -f "$ROOT/docs/CODE_TOUR.md" ]]; then
  cp -f "$ROOT/docs/CODE_TOUR.md" "$OUT_DIR/docs/CODE_TOUR.md"
fi
if [[ -f "$ROOT/final-release/ACCEPTANCE_MATRIX.md" ]]; then
  cp -f "$ROOT/final-release/ACCEPTANCE_MATRIX.md" "$OUT_DIR/ACCEPTANCE_MATRIX.md"
fi
cp -f "$ROOT/final-release/FINAL_CLAIMS.md" "$OUT_DIR/Results-and-Methodology.md"
cp -f "$ROOT/final-release/JUDGE_QA.md" "$OUT_DIR/Judge-QA.md" 2>/dev/null || true
cp -f "$ROOT/final-release/DEMO_SCRIPT.md" "$OUT_DIR/Demo-Video-Script.md" 2>/dev/null || true
cp -f "$ROOT/final-release/PROPOSAL_ABSTRACT.md" "$OUT_DIR/PROPOSAL_ABSTRACT.md" 2>/dev/null || true

if [[ -f "$ROOT/final-release/demo-video/Eco-Loop-Demo-Walkthrough.mp4" ]]; then
  cp -f "$ROOT/final-release/demo-video/Eco-Loop-Demo-Walkthrough.mp4" "$OUT_DIR/Eco-Loop-Demo-Walkthrough.mp4"
fi

if [[ -f "$ROOT/final-release/GitHub-and-Live-Links.md" ]]; then
  cp -f "$ROOT/final-release/GitHub-and-Live-Links.md" "$OUT_DIR/GitHub-and-Live-Links.md"
else
  cat > "$OUT_DIR/GitHub-and-Live-Links.md" <<'EOF'
# GitHub and live links

- GitHub: https://github.com/alphasafal/Twincity-
- Live demo: https://twinpilot.webyaar.in
- Authoritative metrics: Path A comfort-zero EnergyPlus experiment
- Hybrid Path C proves LLM supervisory involvement in the closed loop
EOF
fi

if [[ -f "$ROOT/final-release/Demo-Video-Link.md" ]]; then
  cp -f "$ROOT/final-release/Demo-Video-Link.md" "$OUT_DIR/Demo-Video-Link.md"
else
  cat > "$OUT_DIR/Demo-Video-Link.md" <<'EOF'
# Demo video

See `Eco-Loop-Demo-Walkthrough.mp4` in this package.
EOF
fi

# Building models (baseline IDF + runtime-modified schedule artifacts)
# Skip bulky .epw weather file in the upload ZIP — full weather lives on GitHub.
cp -f "$ROOT/building-models/sample-office/office_5zone.idf" "$OUT_DIR/building-models/base-office.idf"
cat > "$OUT_DIR/building-models/EPW-NOTE.txt" <<'EOF'
Weather file (chicago.epw) is on GitHub at building-models/weather/chicago.epw
to keep this upload ZIP small. Baseline IDF is included as base-office.idf.
EOF
if [[ -d "$ROOT/final-release/evidence/building-models" ]]; then
  mkdir -p "$OUT_DIR/building-models/runtime-modified"
  cp -f "$ROOT/final-release/evidence/building-models/"* "$OUT_DIR/building-models/runtime-modified/" 2>/dev/null || true
fi

# Results (Path A authoritative + scenarios + hybrid if present)
if [[ -f "$ROOT/results/comparison/comparison.json" ]]; then
  cp -f "$ROOT/results/comparison/comparison.json" "$OUT_DIR/results/comparison.json"
fi
if [[ -f "$ROOT/results/baseline/summary.json" ]]; then
  cp -f "$ROOT/results/baseline/summary.json" "$OUT_DIR/results/baseline-summary.json"
fi
if [[ -f "$ROOT/results/agent/summary.json" ]]; then
  cp -f "$ROOT/results/agent/summary.json" "$OUT_DIR/results/agent-summary.json"
fi
if [[ -f "$ROOT/results/agent/actions.json" ]]; then
  "$ROOT/.venv/bin/python" - <<'PY' || true
import json, csv
from pathlib import Path
root = Path("/workspace")
actions = json.loads((root/"results/agent/actions.json").read_text())
out = Path("/workspace/Eco-Loop-Hackathon-Submission/results/action-log.csv")
if isinstance(actions, list) and actions:
    keys = sorted({k for row in actions if isinstance(row, dict) for k in row})
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        for row in actions:
            if isinstance(row, dict):
                w.writerow(row)
PY
fi
if [[ -f "$ROOT/results/agent/comfort_analysis.json" ]]; then
  cp -f "$ROOT/results/agent/comfort_analysis.json" "$OUT_DIR/results/comfort-analysis.json"
fi
if [[ -f "$ROOT/results/scenarios/consolidated_comparison.json" ]]; then
  cp -f "$ROOT/results/scenarios/consolidated_comparison.json" "$OUT_DIR/results/scenario-comparison.json"
fi
if [[ -f "$ROOT/results/hybrid/summary.json" ]]; then
  mkdir -p "$OUT_DIR/results/hybrid"
  cp -f "$ROOT/results/hybrid/summary.json" "$OUT_DIR/results/hybrid/summary.json"
  if [[ -f "$ROOT/results/hybrid/self_correction.jsonl" ]]; then
    head -n 40 "$ROOT/results/hybrid/self_correction.jsonl" > "$OUT_DIR/results/hybrid/self_correction.sample.jsonl"
  fi
fi
# Sealed evidence fallback when live results/ are empty
if [[ ! -f "$OUT_DIR/results/comparison.json" && -f "$ROOT/final-release/evidence/energyplus/comparison.json" ]]; then
  cp -f "$ROOT/final-release/evidence/energyplus/comparison.json" "$OUT_DIR/results/comparison.json"
fi
if [[ ! -f "$OUT_DIR/results/baseline-summary.json" && -f "$ROOT/final-release/evidence/energyplus/baseline-summary.json" ]]; then
  cp -f "$ROOT/final-release/evidence/energyplus/baseline-summary.json" "$OUT_DIR/results/baseline-summary.json"
fi
if [[ ! -f "$OUT_DIR/results/agent-summary.json" && -f "$ROOT/final-release/evidence/energyplus/agent-summary.json" ]]; then
  cp -f "$ROOT/final-release/evidence/energyplus/agent-summary.json" "$OUT_DIR/results/agent-summary.json"
fi
if [[ -f "$ROOT/final-release/evidence/independent-metrics.json" ]]; then
  cp -f "$ROOT/final-release/evidence/independent-metrics.json" "$OUT_DIR/results/independent-metrics.json"
fi
if [[ ! -f "$OUT_DIR/results/hybrid/summary.json" && -f "$ROOT/final-release/evidence/hybrid/summary.json" ]]; then
  mkdir -p "$OUT_DIR/results/hybrid"
  cp -f "$ROOT/final-release/evidence/hybrid/summary.json" "$OUT_DIR/results/hybrid/"
  if [[ -f "$ROOT/final-release/evidence/hybrid/self_correction.jsonl" ]]; then
    head -n 40 "$ROOT/final-release/evidence/hybrid/self_correction.jsonl" > "$OUT_DIR/results/hybrid/self_correction.sample.jsonl"
  fi
fi

# Evidence (compact samples — full traces on GitHub)
cp -f "$ROOT/final-release/evidence/final-actuator-trace.csv" "$OUT_DIR/evidence/actuator-trace.csv" 2>/dev/null || true
if [[ -f "$ROOT/final-release/evidence/mcp-runtime-trace.jsonl" ]]; then
  head -n 80 "$ROOT/final-release/evidence/mcp-runtime-trace.jsonl" > "$OUT_DIR/evidence/mcp-runtime-trace.sample.jsonl"
fi
cp -f "$ROOT/final-release/evidence/safety-rejection.log" "$OUT_DIR/evidence/safety-rejection.txt" 2>/dev/null || true
cp -f "$ROOT/final-release/evidence/ollama-fallback.log" "$OUT_DIR/evidence/fallback-proof.txt" 2>/dev/null || true
if [[ -f "$ROOT/results/hybrid/mcp-runtime-trace.jsonl" ]]; then
  head -n 80 "$ROOT/results/hybrid/mcp-runtime-trace.jsonl" > "$OUT_DIR/evidence/hybrid-mcp-runtime-trace.sample.jsonl"
elif [[ -f "$ROOT/final-release/evidence/hybrid/mcp-runtime-trace.jsonl" ]]; then
  head -n 80 "$ROOT/final-release/evidence/hybrid/mcp-runtime-trace.jsonl" > "$OUT_DIR/evidence/hybrid-mcp-runtime-trace.sample.jsonl"
fi
cp -f "$ROOT/final-release/FINAL_LIMITATIONS.md" "$OUT_DIR/docs/LIMITATIONS.md" 2>/dev/null || true

# D1 — lean source (upload-size safe). Full monorepo is on GitHub.
mkdir -p "$OUT_DIR/source"
copy_tree() {
  local src="$1" dest="$2"
  if [[ -d "$src" ]]; then
    mkdir -p "$dest"
    rsync -a \
      --exclude 'node_modules' \
      --exclude '.next' \
      --exclude '.venv' \
      --exclude '__pycache__' \
      --exclude '*.pyc' \
      --exclude '.env' \
      --exclude '.env.local' \
      --exclude '*.pem' \
      --exclude '.turbo' \
      --exclude 'dist' \
      --exclude 'coverage' \
      --exclude '*.egg-info' \
      --exclude '*.db' \
      --exclude '*.sqlite' \
      --exclude '*.sqlite3' \
      --exclude 'tests' \
      --exclude '*.epw' \
      "$src/" "$dest/"
  fi
}

copy_tree "$ROOT/services/simulator" "$OUT_DIR/source/services/simulator"
copy_tree "$ROOT/services/agent" "$OUT_DIR/source/services/agent"
copy_tree "$ROOT/services/mcp-server" "$OUT_DIR/source/services/mcp-server"
copy_tree "$ROOT/services/optimizer" "$OUT_DIR/source/services/optimizer"
mkdir -p "$OUT_DIR/source/scripts"
for f in \
  hybrid_supervisory_loop.py \
  llm_mcp_loop.py \
  run_hybrid_supervisory_experiment.sh \
  run_llm_mcp_experiment.sh \
  run_baseline.sh \
  run_agent.sh \
  compare_results.sh \
  run_demo.sh \
  setup_energyplus.sh \
  check_prerequisites.sh
do
  [[ -f "$ROOT/scripts/$f" ]] && cp -f "$ROOT/scripts/$f" "$OUT_DIR/source/scripts/$f"
done
mkdir -p "$OUT_DIR/source/docs"
[[ -f "$ROOT/docs/architecture.md" ]] && cp -f "$ROOT/docs/architecture.md" "$OUT_DIR/source/docs/architecture.md"
[[ -f "$ROOT/docs/CODE_TOUR.md" ]] && cp -f "$ROOT/docs/CODE_TOUR.md" "$OUT_DIR/source/docs/CODE_TOUR.md"

cat > "$OUT_DIR/source/SOURCE_README.md" <<'EOF'
# Eco-Loop source (HirePro D1) — compact upload pack

This ZIP includes the closed-loop Python core. The full monorepo (web dashboard,
API, weather EPW, full MCP traces) is on GitHub:

https://github.com/alphasafal/Twincity-/tree/ecolooop-hackathon-final

| Piece | Path in this ZIP |
|-------|------------------|
| EnergyPlus wrapper / closed loop | `services/simulator/twinpilot_simulator/ep_experiment.py` |
| LLM orchestration (Path C) | `scripts/hybrid_supervisory_loop.py`, `services/agent/` |
| MCP communication bus (stdio) | `services/mcp-server/` |
| SafetyShield | `services/optimizer/twinpilot_optimizer/safety.py` |
EOF

# Hard strip bulky / secret artifacts
find "$OUT_DIR" -name '.env' -delete
find "$OUT_DIR" -name '.env.local' -delete
find "$OUT_DIR" -name '*.pem' -delete
find "$OUT_DIR" \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' -o -name '*.epw' \) -delete
find "$OUT_DIR" -type d -name 'node_modules' -prune -exec rm -rf {} + 2>/dev/null || true
find "$OUT_DIR" -type d -name '.next' -prune -exec rm -rf {} + 2>/dev/null || true
find "$OUT_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true

(
  cd "$(dirname "$OUT_DIR")"
  zip -r -9 "$(basename "$ZIP_PATH")" "$(basename "$OUT_DIR")" \
    -x '*/node_modules/*' '*/.venv/*' '*/__pycache__/*' '*/.next/*' '*.pyc' '*/.env' '*/.env.local' '*.db' '*.sqlite3' '*.epw'
)

echo "Wrote $ZIP_PATH"
ls -lh "$ZIP_PATH"
