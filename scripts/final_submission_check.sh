#!/usr/bin/env bash
# Validate final-release submission package completeness and hygiene.
# Non-destructive. Does not push/tag.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PKG="$ROOT/final-release/submission-package"
FR="$ROOT/final-release"
fail=0

echo "== Eco-Loop final submission check =="
echo "UTC=$(date -u +%Y-%m-%dT%H:%M:%SZ)"

require_file() {
  local f="$1"
  if [[ ! -f "$f" ]]; then
    echo "FAIL missing: $f"
    fail=1
    return
  fi
  if [[ ! -s "$f" ]]; then
    echo "FAIL empty: $f"
    fail=1
    return
  fi
  echo "PASS exists+nonempty: $f"
}

REQUIRED=(
  "$FR/FINAL_RELEASE_REPORT.md"
  "$FR/FINAL_RELEASE_MANIFEST.json"
  "$FR/FINAL_OWNER_CHECKLIST.md"
  "$FR/FINAL_DEMO_SCRIPT.md"
  "$FR/FINAL_JUDGE_QA.md"
  "$FR/FINAL_LIMITATIONS.md"
  "$FR/FINAL_CLAIMS.md"
  "$FR/FINAL_COMMAND_REFERENCE.md"
  "$FR/PRESENTATION_CONTENT.md"
  "$FR/SUBMISSION_FILE_CHECKLIST.md"
  "$FR/SECURITY_AND_PRIVACY_CHECK.md"
  "$FR/RELEASE_NOTES.md"
  "$FR/checksums/SHA256SUMS.txt"
  "$PKG/README.md"
  "$PKG/FINAL_RELEASE_REPORT.md"
  "$PKG/FINAL_CLAIMS.md"
  "$PKG/FINAL_LIMITATIONS.md"
  "$PKG/FINAL_DEMO_SCRIPT.md"
  "$PKG/FINAL_JUDGE_QA.md"
  "$PKG/PRESENTATION_CONTENT.md"
)

for f in "${REQUIRED[@]}"; do
  require_file "$f"
done

# Secret scan on submission package + final-release docs
echo "-- secret scan --"
if rg -n -i --hidden \
  -g '!.git' \
  '(api[_-]?key\s*[:=]\s*['\''\"][^'\''\"]+['\''\"]|sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|BEGIN (RSA |OPENSSH )?PRIVATE KEY)' \
  "$FR" 2>/dev/null | head -20; then
  echo "FAIL secret-like pattern detected"
  fail=1
else
  echo "PASS no high-confidence secret patterns in final-release/"
fi

# Forbidden artifacts
echo "-- forbidden artifacts --"
if find "$PKG" -type d \( -name node_modules -o -name .venv -o -name __pycache__ \) | grep -q .; then
  echo "FAIL package contains venv/node_modules/__pycache__"
  fail=1
else
  echo "PASS no venv/node_modules in package"
fi
if find "$PKG" -name '.env' -o -name '*.pid' | grep -q .; then
  echo "FAIL package contains .env or pid files"
  fail=1
else
  echo "PASS no .env/pid in package"
fi

# Stale intermediate commit claims inside final-release (allow historical mentions with context)
echo "-- stale final-release commit wording --"
if rg -n 'final release commit.*(9085cbc|95a58e7|1b6a045|b63311c)' "$FR"/*.md "$FR"/*.json 2>/dev/null; then
  echo "FAIL intermediate commit incorrectly labeled as final release"
  fail=1
else
  echo "PASS no intermediate commit labeled as final release"
fi

# Manifest parse
"$ROOT/.venv/bin/python" - <<'PY' || fail=1
import json
from pathlib import Path
m=json.loads(Path("final-release/FINAL_RELEASE_MANIFEST.json").read_text())
assert m.get("final_release_commit"), "missing final_release_commit"
assert m.get("overall_status") in {"PASS","CONDITIONAL_PASS","FAIL"}
assert isinstance(m.get("authoritative_results"), dict)
print("PASS manifest structure", m["overall_status"], m["final_release_commit"][:12])
PY

# Checksums verify if possible
if [[ -f "$FR/checksums/SHA256SUMS.txt" ]]; then
  if (cd "$FR" && sha256sum -c checksums/SHA256SUMS.txt --quiet); then
    echo "PASS checksums verify"
  else
    echo "FAIL checksum mismatch"
    fail=1
  fi
fi

if [[ $fail -ne 0 ]]; then
  echo "SUBMISSION CHECK: FAIL"
  exit 1
fi
echo "SUBMISSION CHECK: PASS"
exit 0
