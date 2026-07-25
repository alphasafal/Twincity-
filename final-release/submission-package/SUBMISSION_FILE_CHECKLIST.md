# Submission File Checklist

**Commit:** `f0f94d84d08969784cf2373ddbb3cca6e3fa909b` · **Generated:** 2026-07-25T12:01:39.455435+00:00

| File | Exists | Non-empty | Notes |
|---|---|---|---|
| `FINAL_RELEASE_REPORT.md` | True | True | |
| `FINAL_RELEASE_MANIFEST.json` | True | True | |
| `FINAL_OWNER_CHECKLIST.md` | True | True | |
| `FINAL_DEMO_SCRIPT.md` | True | True | |
| `FINAL_JUDGE_QA.md` | True | True | |
| `FINAL_LIMITATIONS.md` | True | True | |
| `FINAL_CLAIMS.md` | True | True | |
| `FINAL_COMMAND_REFERENCE.md` | True | True | |
| `PRESENTATION_CONTENT.md` | True | True | |
| `SUBMISSION_FILE_CHECKLIST.md` | True | True | |
| `SECURITY_AND_PRIVACY_CHECK.md` | True | True | |
| `RELEASE_NOTES.md` | True | True | |
| `checksums/SHA256SUMS.txt` | True | True | |
| `submission-package/README.md` | True | True | |
| `submission-package/FINAL_CLAIMS.md` | True | True | |
| `evidence/independent-metrics.json` | True | True | |
| `evidence/final-actuator-trace.csv` | True | True | |
| `evidence/mcp-runtime-trace.jsonl` | True | True | |
| `evidence/safety-rejection.log` | True | True | |
| `evidence/ollama-fallback.log` | True | True | |

## Automated checks
- Run `./scripts/final_submission_check.sh`
- Confirm no secrets / no `.env` / no node_modules in package
- Confirm no intermediate commit mislabeled as final release
- Confirm Path A numbers match independent-metrics.json

## Stale-commit policy
- Authoritative sealed commit must be recorded in FINAL_RELEASE_MANIFEST.json.
- Historical commits (b63311c, 9085cbc, 95a58e7, 1b6a045, 133b053 pre-seal) are history only unless selected as tip.
