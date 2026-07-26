#!/usr/bin/env bash
# Build a HirePro upload pack that contains PDF files only (+ a ZIP of those PDFs).
# Demo video stays on GitHub / README — not inside the PDF pack.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

CHROME="${CHROME:-$(command -v google-chrome || command -v chromium || true)}"
[[ -n "$CHROME" ]] || { echo "google-chrome required" >&2; exit 1; }

OUT_DIR="$ROOT/final-release/pdf-pack"
ZIP_PATH="$ROOT/Eco-Loop-Hackathon-PDFs.zip"
HTML_DIR="$(mktemp -d /tmp/eco-pdf-html-XXXXXX)"
mkdir -p "$OUT_DIR"
rm -f "$ZIP_PATH"

chrome_pdf() {
  local html="$1" pdf="$2"
  local userdata
  userdata="$(mktemp -d /tmp/eco-chrome-XXXXXX)"
  set +e
  timeout 45s "$CHROME" \
    --headless=new \
    --disable-gpu \
    --no-sandbox \
    --disable-dev-shm-usage \
    --no-first-run \
    --no-default-browser-check \
    --hide-scrollbars \
    --no-pdf-header-footer \
    --user-data-dir="$userdata" \
    --print-to-pdf="$pdf" \
    "file://${html}" >/tmp/eco-pdf-chrome.log 2>&1
  local rc=$?
  set -e
  rm -rf "$userdata"
  if [[ ! -s "$pdf" ]]; then
    echo "Failed to render $pdf (rc=$rc)" >&2
    tail -30 /tmp/eco-pdf-chrome.log >&2 || true
    exit 1
  fi
}

# --- copy already-final PDFs ---
cp -f "$ROOT/final-release/presentation/Eco-Loop_Building_Agents.pdf" \
  "$OUT_DIR/01-IDEA-Presentation-Eco-Loop_Building_Agents.pdf"
cp -f "$ROOT/final-release/presentation/Architecture-Document.pdf" \
  "$OUT_DIR/02-Architecture-Document.pdf"

python3 - "$HTML_DIR" "$OUT_DIR" <<'PY'
import json, html, sys
from pathlib import Path

html_dir = Path(sys.argv[1])
out_dir = Path(sys.argv[2])
root = Path("/workspace")
html_dir.mkdir(parents=True, exist_ok=True)

def md_escape(s: str) -> str:
    return html.escape(s)

def write_doc(name: str, title: str, body_html: str):
    doc = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"/>
<title>{md_escape(title)}</title>
<style>
  @page {{ margin: 18mm; }}
  body {{ font-family: Georgia, 'Times New Roman', serif; color: #111; line-height: 1.45; font-size: 12pt; }}
  h1 {{ font-size: 20pt; margin: 0 0 8px; }}
  h2 {{ font-size: 14pt; margin: 18px 0 8px; border-bottom: 1px solid #ccc; padding-bottom: 4px; }}
  p, li {{ font-size: 11pt; }}
  code, pre {{ font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 9.5pt; }}
  pre {{ background: #f6f6f6; padding: 10px; white-space: pre-wrap; word-break: break-word; }}
  table {{ border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 10.5pt; }}
  th, td {{ border: 1px solid #bbb; padding: 6px 8px; text-align: left; vertical-align: top; }}
  th {{ background: #f0f0f0; }}
  .muted {{ color: #555; font-size: 10pt; }}
</style></head><body>
<h1>{md_escape(title)}</h1>
<p class="muted">Eco-Loop / TwinPilot · HirePro Honeywell · https://github.com/alphasafal/Twincity-/tree/ecolooop-hackathon-final</p>
{body_html}
</body></html>"""
    (html_dir / name).write_text(doc, encoding="utf-8")

# 03 Results
comp = json.loads((root / "final-release/evidence/energyplus/comparison.json").read_text())
indep = {}
ip = root / "final-release/evidence/independent-metrics.json"
if ip.exists():
    indep = json.loads(ip.read_text())
claims = (root / "final-release/FINAL_CLAIMS.md").read_text(encoding="utf-8", errors="replace")[:6000]
write_doc(
    "03-results.html",
    "Quantitative Savings Results (Path A)",
    f"""
<h2>Authoritative Path A metrics (comfort-zero)</h2>
<table>
<tr><th>Metric</th><th>Baseline</th><th>Agent</th><th>% reduction</th></tr>
<tr><td>Total energy (kWh)</td><td>{comp['total_energy_kwh']['baseline']}</td><td>{comp['total_energy_kwh']['agent']}</td><td>{comp['total_energy_kwh']['percent_reduction']:.2f}%</td></tr>
<tr><td>HVAC energy (kWh)</td><td>{comp['hvac_energy_kwh']['baseline']}</td><td>{comp['hvac_energy_kwh']['agent']}</td><td>{comp['hvac_energy_kwh']['percent_reduction']:.2f}%</td></tr>
<tr><td>Peak power (kW)</td><td>{comp['peak_power_kw']['baseline']}</td><td>{comp['peak_power_kw']['agent']}</td><td>{comp['peak_power_kw']['percent_reduction']:.2f}%</td></tr>
<tr><td>Comfort violation hours</td><td>{comp['occupied_comfort_violation_hours']['baseline']}</td><td>{comp['occupied_comfort_violation_hours']['agent']}</td><td>0</td></tr>
</table>
<p><b>Speak line:</b> AI proposes. SafetyShield validates. EnergyPlus executes.</p>
<p class="muted">Live dashboard: https://twinpilot.webyaar.in (login manager@twinpilot.demo)</p>
<h2>Claims / methodology excerpt</h2>
<pre>{md_escape(claims)}</pre>
""",
)

# 04 Building models
note = ""
np = root / "final-release/evidence/building-models/runtime-modified-model-note.md"
if np.exists():
    note = np.read_text(encoding="utf-8", errors="replace")
write_doc(
    "04-building-models.html",
    "Building Models (.idf) — Baseline & Runtime-Modified Evidence",
    f"""
<h2>Baseline model</h2>
<p>Repository path: <code>building-models/sample-office/office_5zone.idf</code></p>
<p>Weather: <code>building-models/weather/chicago.epw</code> (on GitHub)</p>
<h2>Runtime-modified control evidence</h2>
<p>EnergyPlus Runtime API writes cooling setpoints to actuator <code>Clg-SetP-Sch</code>
(schedule values), so the on-disk IDF text is not rewritten. Evidence of the modified
control schedule is sealed under <code>final-release/evidence/building-models/</code>.</p>
<pre>{md_escape(note)}</pre>
<p>Also see: <code>runtime-modified-clg-setp-sch.json</code>, <code>post-control-cooling-schedule.csv</code> on GitHub.</p>
""",
)

# 05 Source overview
tour = (root / "docs/CODE_TOUR.md").read_text(encoding="utf-8", errors="replace") if (root / "docs/CODE_TOUR.md").exists() else ""
write_doc(
    "05-source-code-overview.html",
    "Fully Functional Source Code — Overview for Judges",
    f"""
<h2>GitHub (full source)</h2>
<p><code>https://github.com/alphasafal/Twincity-/tree/ecolooop-hackathon-final</code></p>
<table>
<tr><th>Deliverable piece</th><th>Path</th></tr>
<tr><td>EnergyPlus wrapper / closed loop</td><td><code>services/simulator/twinpilot_simulator/ep_experiment.py</code></td></tr>
<tr><td>LLM orchestration (Path C)</td><td><code>scripts/hybrid_supervisory_loop.py</code>, <code>services/agent/</code></td></tr>
<tr><td>MCP communication bus (stdio)</td><td><code>services/mcp-server/</code></td></tr>
<tr><td>SafetyShield</td><td><code>services/optimizer/twinpilot_optimizer/safety.py</code></td></tr>
<tr><td>Savings dashboard</td><td><code>apps/web/</code> · live https://twinpilot.webyaar.in</td></tr>
</table>
<h2>Code tour</h2>
<pre>{md_escape(tour[:8000])}</pre>
""",
)

# 06 Demo video pointer
write_doc(
    "06-Demo-Video-Link.html",
    "PoC Demonstration Video (≤3 minutes)",
    """
<h2>Watch on GitHub / README</h2>
<p>The MP4 is hosted in the repository (not duplicated as a non-PDF upload):</p>
<p><b>Direct video:</b><br/>
<code>https://github.com/alphasafal/Twincity-/blob/ecolooop-hackathon-final/final-release/demo-video/Eco-Loop-Demo-Walkthrough.mp4</code></p>
<p><b>README (embedded preview / link):</b><br/>
<code>https://github.com/alphasafal/Twincity-/tree/ecolooop-hackathon-final#poc-demo-video</code></p>
<p>Duration: ~180 seconds. Narrative: EnergyPlus → MCP → LLM/controller → SafetyShield → actuator → next state.</p>
<p class="muted">Live interactive demo: https://twinpilot.webyaar.in</p>
""",
)

# 07 Acceptance
acc = (root / "final-release/ACCEPTANCE_MATRIX.md").read_text(encoding="utf-8", errors="replace")
write_doc("07-Acceptance-Matrix.html", "HirePro Acceptance Matrix", f"<pre>{md_escape(acc)}</pre>")

# 08 Judge QA
jq = (root / "final-release/JUDGE_QA.md").read_text(encoding="utf-8", errors="replace") if (root / "final-release/JUDGE_QA.md").exists() else ""
write_doc("08-Judge-QA.html", "Judge Q&A", f"<pre>{md_escape(jq[:10000])}</pre>")

# 09 Submission index
write_doc(
    "00-Submission-Index.html",
    "Eco-Loop HirePro — PDF Submission Index",
    """
<h2>Upload these PDFs</h2>
<table>
<tr><th>#</th><th>File</th><th>Maps to deliverable</th></tr>
<tr><td>00</td><td>00-Submission-Index.pdf</td><td>This index</td></tr>
<tr><td>01</td><td>01-IDEA-Presentation-Eco-Loop_Building_Agents.pdf</td><td>Official IDEA presentation (6 slides)</td></tr>
<tr><td>02</td><td>02-Architecture-Document.pdf</td><td>System architecture document</td></tr>
<tr><td>03</td><td>03-Quantitative-Savings-Results.pdf</td><td>Savings dashboard / export proof</td></tr>
<tr><td>04</td><td>04-Building-Models.pdf</td><td>Baseline + runtime-modified model evidence</td></tr>
<tr><td>05</td><td>05-Source-Code-Overview.pdf</td><td>Source map (full code on GitHub)</td></tr>
<tr><td>06</td><td>06-Demo-Video-Link.pdf</td><td>PoC video link (video plays from README/GitHub)</td></tr>
<tr><td>07</td><td>07-Acceptance-Matrix.pdf</td><td>Checklist</td></tr>
<tr><td>08</td><td>08-Judge-QA.pdf</td><td>Judge FAQ</td></tr>
</table>
<h2>GitHub + live demo</h2>
<ul>
<li>GitHub: https://github.com/alphasafal/Twincity-/tree/ecolooop-hackathon-final</li>
<li>Live demo: https://twinpilot.webyaar.in — manager@twinpilot.demo / TwinPilot-Manager-Demo!</li>
<li>Demo video section in README: anchor <code>#poc-demo-video</code></li>
</ul>
""",
)
print("html ready", html_dir)
PY

# Render HTML → PDF
chrome_pdf "$HTML_DIR/00-Submission-Index.html" "$OUT_DIR/00-Submission-Index.pdf"
chrome_pdf "$HTML_DIR/03-results.html" "$OUT_DIR/03-Quantitative-Savings-Results.pdf"
chrome_pdf "$HTML_DIR/04-building-models.html" "$OUT_DIR/04-Building-Models.pdf"
chrome_pdf "$HTML_DIR/05-source-code-overview.html" "$OUT_DIR/05-Source-Code-Overview.pdf"
chrome_pdf "$HTML_DIR/06-Demo-Video-Link.html" "$OUT_DIR/06-Demo-Video-Link.pdf"
chrome_pdf "$HTML_DIR/07-Acceptance-Matrix.html" "$OUT_DIR/07-Acceptance-Matrix.pdf"
chrome_pdf "$HTML_DIR/08-Judge-QA.html" "$OUT_DIR/08-Judge-QA.pdf"

# ZIP of PDFs only
(
  cd "$OUT_DIR"
  zip -r -9 "$ZIP_PATH" ./*.pdf
)

echo "PDF pack:"
ls -lh "$OUT_DIR"/*.pdf
echo "ZIP:"
ls -lh "$ZIP_PATH"
rm -rf "$HTML_DIR"
