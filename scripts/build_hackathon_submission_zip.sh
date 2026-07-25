#!/usr/bin/env bash
# Build Eco-Loop-Hackathon-Submission.zip (no secrets, no node_modules, no .env).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUT_DIR="${1:-$ROOT/Eco-Loop-Hackathon-Submission}"
ZIP_PATH="${2:-$ROOT/Eco-Loop-Hackathon-Submission.zip}"
rm -rf "$OUT_DIR" "$ZIP_PATH"
mkdir -p "$OUT_DIR"/{building-models,results,evidence,docs}

# Markdown deliverables (PDF conversion is owner-side if needed)
cp -f "$ROOT/README.md" "$OUT_DIR/README.md"
cp -f "$ROOT/final-release/PRESENTATION_CONTENT.md" "$OUT_DIR/Eco-Loop-Presentation.md"
cp -f "$ROOT/docs/architecture.md" "$OUT_DIR/Architecture-Document.md" 2>/dev/null || \
  cp -f "$ROOT/final-release/FINAL_RELEASE_REPORT.md" "$OUT_DIR/Architecture-Document.md"
cp -f "$ROOT/final-release/FINAL_CLAIMS.md" "$OUT_DIR/Results-and-Methodology.md"
cp -f "$ROOT/final-release/JUDGE_QA.md" "$OUT_DIR/Judge-QA.md" 2>/dev/null || true
cp -f "$ROOT/final-release/DEMO_SCRIPT.md" "$OUT_DIR/Demo-Video-Script.md" 2>/dev/null || true
cp -f "$ROOT/final-release/PROPOSAL_ABSTRACT.md" "$OUT_DIR/PROPOSAL_ABSTRACT.md" 2>/dev/null || true

cat > "$OUT_DIR/GitHub-and-Live-Links.md" <<'EOF'
# GitHub and live links

- Primary proof: GitHub repository + release tag `hackathon-final-v1`
- Temporary Cloudflare demo URLs are optional and may expire
- Authoritative metrics: Path A comfort-zero EnergyPlus experiment
- Hybrid Path C proves LLM supervisory involvement in the closed loop
EOF

cat > "$OUT_DIR/Demo-Video-Link.md" <<'EOF'
# Demo video

Replace this file with the permanent hosted link before submission.

Required narrative (≤3 minutes):
EnergyPlus observation → MCP tools/call → Ollama strategy → deterministic optimiser →
SafetyShield → Clg-SetP-Sch → next EnergyPlus state → results (4.98% HVAC, 0 comfort violations).
EOF

# Building models
cp -f "$ROOT/building-models/sample-office/office_5zone.idf" "$OUT_DIR/building-models/base-office.idf"
cp -f "$ROOT/building-models/weather/chicago.epw" "$OUT_DIR/building-models/chicago.epw" 2>/dev/null || \
  echo "EPW referenced at building-models/weather/chicago.epw in the repository" > "$OUT_DIR/building-models/EPW-NOTE.txt"

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

# Evidence
cp -f "$ROOT/final-release/evidence/final-actuator-trace.csv" "$OUT_DIR/evidence/actuator-trace.csv" 2>/dev/null || true
cp -f "$ROOT/final-release/evidence/mcp-runtime-trace.jsonl" "$OUT_DIR/evidence/mcp-runtime-trace.jsonl" 2>/dev/null || true
cp -f "$ROOT/final-release/evidence/safety-rejection.log" "$OUT_DIR/evidence/safety-rejection.txt" 2>/dev/null || true
cp -f "$ROOT/final-release/evidence/ollama-fallback.log" "$OUT_DIR/evidence/fallback-proof.txt" 2>/dev/null || true
if [[ -f "$ROOT/results/hybrid/mcp-runtime-trace.jsonl" ]]; then
  cp -f "$ROOT/results/hybrid/mcp-runtime-trace.jsonl" "$OUT_DIR/evidence/hybrid-mcp-runtime-trace.jsonl"
fi
cp -f "$ROOT/final-release/FINAL_LIMITATIONS.md" "$OUT_DIR/docs/LIMITATIONS.md" 2>/dev/null || true

# Strip secrets if any slipped in
find "$OUT_DIR" -name '.env' -delete
find "$OUT_DIR" -name '*.pem' -delete

(
  cd "$(dirname "$OUT_DIR")"
  zip -r "$(basename "$ZIP_PATH")" "$(basename "$OUT_DIR")" \
    -x '*/node_modules/*' '*/.venv/*' '*/__pycache__/*' '*.pyc'
)

echo "Wrote $ZIP_PATH"
ls -lh "$ZIP_PATH"
