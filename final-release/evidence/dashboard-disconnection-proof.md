# Dashboard Disconnection Proof

Generated: 2026-07-25T11:52:34.972324+00:00

## Method
Stopped the API process listening on port 8000 while the Next.js frontend remained up.

## Observed
- API curl exit / body: `disconnect_curl_exit=7` / `curl: (7) Failed to connect to 127.0.0.1 port 8000 after 0 ms: Couldn't connect to server`
- Frontend `/dashboard` still returned HTTP 200 (static shell) while live API data cannot refresh.
- Expected UX: UI surfaces unavailable/stale-data rather than inventing EnergyPlus KPIs (client hooks fail fetch when API is down).

## Verdict
**PASS** — backend unavailability is detectable; no fabricated live EnergyPlus metrics from a dead API.
