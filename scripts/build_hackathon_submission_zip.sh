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
if [[ -f "$ROOT/final-release/presentation/Eco-Loop-Presentation.pdf" ]]; then
  cp -f "$ROOT/final-release/presentation/Eco-Loop-Presentation.pdf" "$OUT_DIR/Eco-Loop-Presentation.pdf"
fi
# Official HirePro IDEA export (same bytes; keep original filename for judges)
if [[ -f "$ROOT/final-release/presentation/Eco-Loop_Building_Agents.pdf" ]]; then
  cp -f "$ROOT/final-release/presentation/Eco-Loop_Building_Agents.pdf" "$OUT_DIR/Eco-Loop_Building_Agents.pdf"
elif [[ -f "$OUT_DIR/Eco-Loop-Presentation.pdf" ]]; then
  cp -f "$OUT_DIR/Eco-Loop-Presentation.pdf" "$OUT_DIR/Eco-Loop_Building_Agents.pdf"
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

# Building models (baseline + runtime-modified schedule artifacts)
cp -f "$ROOT/building-models/sample-office/office_5zone.idf" "$OUT_DIR/building-models/base-office.idf"
cp -f "$ROOT/building-models/weather/chicago.epw" "$OUT_DIR/building-models/chicago.epw" 2>/dev/null || \
  echo "EPW referenced at building-models/weather/chicago.epw in the repository" > "$OUT_DIR/building-models/EPW-NOTE.txt"
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
  cp -f "$ROOT/results/hybrid/self_correction.jsonl" "$OUT_DIR/results/hybrid/" 2>/dev/null || true
  cp -f "$ROOT/results/hybrid/stage_log.jsonl" "$OUT_DIR/results/hybrid/" 2>/dev/null || true
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
  cp -f "$ROOT/final-release/evidence/hybrid/self_correction.jsonl" "$OUT_DIR/results/hybrid/" 2>/dev/null || true
  cp -f "$ROOT/final-release/evidence/hybrid/stage_log.jsonl" "$OUT_DIR/results/hybrid/" 2>/dev/null || true
fi

# Evidence
cp -f "$ROOT/final-release/evidence/final-actuator-trace.csv" "$OUT_DIR/evidence/actuator-trace.csv" 2>/dev/null || true
cp -f "$ROOT/final-release/evidence/mcp-runtime-trace.jsonl" "$OUT_DIR/evidence/mcp-runtime-trace.jsonl" 2>/dev/null || true
cp -f "$ROOT/final-release/evidence/safety-rejection.log" "$OUT_DIR/evidence/safety-rejection.txt" 2>/dev/null || true
cp -f "$ROOT/final-release/evidence/ollama-fallback.log" "$OUT_DIR/evidence/fallback-proof.txt" 2>/dev/null || true
if [[ -f "$ROOT/results/hybrid/mcp-runtime-trace.jsonl" ]]; then
  cp -f "$ROOT/results/hybrid/mcp-runtime-trace.jsonl" "$OUT_DIR/evidence/hybrid-mcp-runtime-trace.jsonl"
fi
cp -f "$ROOT/final-release/FINAL_LIMITATIONS.md" "$OUT_DIR/docs/LIMITATIONS.md" 2>/dev/null || true

# D1 — fully functional source (no secrets / install artifacts)
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
      "$src/" "$dest/"
  fi
}

copy_tree "$ROOT/services/simulator" "$OUT_DIR/source/services/simulator"
copy_tree "$ROOT/services/agent" "$OUT_DIR/source/services/agent"
copy_tree "$ROOT/services/mcp-server" "$OUT_DIR/source/services/mcp-server"
copy_tree "$ROOT/services/optimizer" "$OUT_DIR/source/services/optimizer"
copy_tree "$ROOT/services/api" "$OUT_DIR/source/services/api"
copy_tree "$ROOT/scripts" "$OUT_DIR/source/scripts"
copy_tree "$ROOT/packages" "$OUT_DIR/source/packages"
copy_tree "$ROOT/apps/web" "$OUT_DIR/source/apps/web"
copy_tree "$ROOT/building-models" "$OUT_DIR/source/building-models"
copy_tree "$ROOT/docs" "$OUT_DIR/source/docs"

# Lightweight repo pointers so judges can rebuild from the ZIP source tree
for f in README.md Makefile package.json pnpm-workspace.yaml turbo.json AGENTS.md; do
  [[ -f "$ROOT/$f" ]] && cp -f "$ROOT/$f" "$OUT_DIR/source/$f"
done
cat > "$OUT_DIR/source/SOURCE_README.md" <<'EOF'
# Eco-Loop source (HirePro D1)

This folder is the fully functional source snapshot for judges:

| Piece | Path |
|-------|------|
| EnergyPlus wrapper / closed loop | `services/simulator/twinpilot_simulator/ep_experiment.py` |
| LLM orchestration (Path C) | `scripts/hybrid_supervisory_loop.py`, `services/agent/` |
| MCP communication bus (stdio) | `services/mcp-server/` |
| SafetyShield | `services/simulator/twinpilot_simulator/safety.py` (and API validation path) |
| Savings dashboard UI | `apps/web/` |

Prefer the GitHub branch for a full clone + `make demo`. Path A savings numbers live in `../results/comparison.json`.
EOF

# Strip secrets if any slipped in
find "$OUT_DIR" -name '.env' -delete
find "$OUT_DIR" -name '.env.local' -delete
find "$OUT_DIR" -name '*.pem' -delete
find "$OUT_DIR" -type d -name 'node_modules' -prune -exec rm -rf {} + 2>/dev/null || true
find "$OUT_DIR" -type d -name '.next' -prune -exec rm -rf {} + 2>/dev/null || true
find "$OUT_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true

(
  cd "$(dirname "$OUT_DIR")"
  zip -r "$(basename "$ZIP_PATH")" "$(basename "$OUT_DIR")" \
    -x '*/node_modules/*' '*/.venv/*' '*/__pycache__/*' '*/.next/*' '*.pyc' '*/.env' '*/.env.local'
)

echo "Wrote $ZIP_PATH"
ls -lh "$ZIP_PATH"
