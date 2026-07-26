# Live demo on twinpilot.webyaar.in

Stable public demo hostname for Eco-Loop / TwinPilot (does **not** replace `webyaar.in`).

| Item | Value |
|------|--------|
| Live demo URL | `https://twinpilot.webyaar.in` |
| Apex site (unchanged) | `https://webyaar.in` |
| Local origin | reverse proxy `127.0.0.1:8080` → Next `:3000` + API `:8000` |
| Tunnel name | `twinpilot-live` |

## Start / keep running (judges)

```bash
./scripts/start_live_demo.sh
# optional: continuous watchdog (recommended while judging is open)
tmux new-session -d -s tp-watchdog './scripts/run_live_demo_watchdog.sh'
```

One-time Cloudflare auth on the host that serves the tunnel:

```bash
cloudflared tunnel login   # select the account that owns webyaar.in
./scripts/start_live_demo.sh
```

## Manual DNS (if CLI route fails)

In Cloudflare Dashboard → **webyaar.in** → DNS → Add record:

| Type | Name | Target | Proxy |
|------|------|--------|-------|
| CNAME | `twinpilot` | `<tunnel-uuid>.cfargotunnel.com` | Proxied (orange cloud) |

## Login for judges

- URL: https://twinpilot.webyaar.in
- Email: `manager@twinpilot.demo`
- Password: `TwinPilot-Manager-Demo!`

## Notes

- Temporary `*.trycloudflare.com` URLs expire; use `twinpilot.webyaar.in` as the submission/live proof.
- Keep the host (API + web + proxy + tunnel + watchdog) running for the judging window.
- Do not point `@` / `www` at this tunnel — leave WebYaar marketing on `webyaar.in`.
- Tunnel credentials stay in `~/.cloudflared/` (never committed).
