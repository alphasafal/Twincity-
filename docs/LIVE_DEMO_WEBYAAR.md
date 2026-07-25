# Live demo on twinpilot.webyaar.in

Stable public demo hostname for Eco-Loop / TwinPilot (does **not** replace `webyaar.in`).

| Item | Value |
|------|--------|
| Live demo URL | `https://twinpilot.webyaar.in` |
| Apex site (unchanged) | `https://webyaar.in` |
| Local origin | reverse proxy `127.0.0.1:8080` → Next `:3000` + API `:8000` |
| Tunnel name | `twinpilot-live` |

## One-time owner auth (required)

This cloud VM cannot edit your Cloudflare DNS until you authorize it.

1. Open the login URL printed by the agent (or run locally on the VM):

```bash
cloudflared tunnel login
```

2. In the browser, select the Cloudflare account that owns **webyaar.in**.
3. Authorize the zone.
4. Tell the agent “login done”, or run:

```bash
./scripts/setup_webyaar_live_demo.sh
```

That script creates the named tunnel, adds the CNAME for `twinpilot.webyaar.in`, updates `apps/web/.env.local`, and starts the tunnel.

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

- Temporary `*.trycloudflare.com` URLs expire; prefer `twinpilot.webyaar.in` as submission/live proof.
- Keep the VM (API + web + proxy + tunnel) running during demos.
- Do not point `@` / `www` at this tunnel — leave WebYaar marketing on `webyaar.in`.
