#!/usr/bin/env bash
# Render presentation PDF + ≤3 min closed-loop demo video for hackathon submission.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PRES_HTML="$ROOT/final-release/presentation/eco-loop-slides.html"
PRES_PDF="$ROOT/final-release/presentation/Eco-Loop-Presentation.pdf"
DEMO_DIR="$ROOT/final-release/demo-video"
ART_DIR="${ART_DIR:-/tmp/twinpilot-artifacts/submission}"
mkdir -p "$DEMO_DIR" "$ART_DIR" "$(dirname "$PRES_PDF")"

CHROME="${CHROME:-$(command -v google-chrome || command -v chromium || true)}"
if [[ -z "$CHROME" ]]; then
  echo "Chrome/Chromium required" >&2
  exit 1
fi

chrome_once() {
  local userdata out_hint="${CHROME_OUT_HINT:-}"
  userdata="$(mktemp -d /tmp/eco-chrome-XXXXXX)"
  set +e
  timeout 30s "$CHROME" \
    --headless=new \
    --disable-gpu \
    --no-sandbox \
    --disable-dev-shm-usage \
    --no-first-run \
    --no-default-browser-check \
    --disable-extensions \
    --disable-background-networking \
    --disable-sync \
    --disable-translate \
    --hide-scrollbars \
    --virtual-time-budget=2000 \
    --user-data-dir="$userdata" \
    "$@" >/tmp/eco-chrome-last.log 2>&1
  local rc=$?
  set -e
  rm -rf "$userdata"
  # 124 = timeout; accept if caller already has the artifact
  if [[ $rc -eq 0 || $rc -eq 124 ]]; then
    return 0
  fi
  echo "Chrome failed (rc=$rc). Log:" >&2
  tail -40 /tmp/eco-chrome-last.log >&2 || true
  return "$rc"
}

echo "==> Rendering presentation PDF"
chrome_once \
  --no-pdf-header-footer \
  --print-to-pdf="$PRES_PDF" \
  "file://$PRES_HTML"
test -s "$PRES_PDF"
ls -lh "$PRES_PDF"
cp -f "$PRES_PDF" "$ART_DIR/Eco-Loop-Presentation.pdf"

echo "==> Preparing capture HTML"
python3 - <<'PY'
from pathlib import Path
src = Path("/workspace/final-release/demo-video/closed-loop-walkthrough.html").read_text()
src = src.replace(
    "const started = performance.now();\n    const TOTAL = 180;",
    """const params = new URLSearchParams(location.search);
    const FORCE_T = Number(params.get('t') || '0');
    const started = performance.now() - FORCE_T * 1000;
    const TOTAL = 180;
    window.__FORCE_T = FORCE_T;""",
)
src = src.replace(
    "if (t < TOTAL + 0.5) requestAnimationFrame(tick);",
    "if (!('__FORCE_T' in window) && t < TOTAL + 0.5) requestAnimationFrame(tick);",
)
Path("/workspace/final-release/demo-video/closed-loop-capture.html").write_text(src)
print("wrote capture html")
PY

FRAMES_DIR="$DEMO_DIR/frames"
rm -rf "$FRAMES_DIR"
mkdir -p "$FRAMES_DIR"
CAPTURE_HTML="$DEMO_DIR/closed-loop-capture.html"

# Narrative keyframes: time_seconds:hold_seconds:label
# Total hold ≈ 22+26+47+35+35+15 = 180s
KEYFRAMES=(
  "2:22:problem"
  "30:26:architecture"
  "70:47:loop"
  "105:35:results"
  "145:35:safety"
  "172:15:close"
)

echo "==> Capturing key narrative frames"
CONCAT_LIST="$DEMO_DIR/concat.txt"
: > "$CONCAT_LIST"

for entry in "${KEYFRAMES[@]}"; do
  IFS=':' read -r t hold label <<<"$entry"
  out=$(printf "%s/%s.png" "$FRAMES_DIR" "$label")
  chrome_once \
    --window-size=1280,720 \
    --screenshot="$out" \
    "file://$CAPTURE_HTML?t=$t"
  if [[ ! -f "$out" ]]; then
    if [[ -f screenshot.png ]]; then
      mv screenshot.png "$out"
    elif [[ -f "$ROOT/screenshot.png" ]]; then
      mv "$ROOT/screenshot.png" "$out"
    fi
  fi
  test -s "$out"
  echo "  $label @ t=${t}s (hold ${hold}s) -> $out"
  # ffmpeg concat demuxer: file + duration
  {
    echo "file '$out'"
    echo "duration $hold"
  } >> "$CONCAT_LIST"
  cp -f "$out" "$ART_DIR/demo-still-${label}.png"
  cp -f "$out" "$DEMO_DIR/demo-still-${label}.png"
done
# concat demuxer requires repeating the last file without duration
last_png=$(ls -1 "$FRAMES_DIR"/close.png)
echo "file '$last_png'" >> "$CONCAT_LIST"

DEMO_MP4="$DEMO_DIR/Eco-Loop-Demo-Walkthrough.mp4"
echo "==> Encoding demo video (~180s)"
ffmpeg -y -f concat -safe 0 -i "$CONCAT_LIST" \
  -vf "fps=30,format=yuv420p" \
  -c:v libx264 -pix_fmt yuv420p -movflags +faststart \
  "$DEMO_MP4"

ls -lh "$DEMO_MP4"
cp -f "$DEMO_MP4" "$ART_DIR/Eco-Loop-Demo-Walkthrough.mp4"

# duration check
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$DEMO_MP4" | tee "$DEMO_DIR/duration.txt"

echo "DONE"
echo "PDF=$PRES_PDF"
echo "VIDEO=$DEMO_MP4"
