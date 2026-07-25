# Security and Privacy Check

Generated: 2026-07-25T12:01:39.455435+00:00
Release commit (candidate): `29e88cbd829a333b4661ea8d6c448b1a02a46325`
Branch: `cursor/ecolooop-energyplus-audit-b6b3`

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
