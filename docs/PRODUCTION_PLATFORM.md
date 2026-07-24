# TwinPilot Production Platform

Multi-tenant B2B SaaS control plane with vendor-agnostic BMS connectors and Honeywell as the first certified adapter.

## Architecture

- **Tenancy:** `Organization` → `Membership` → `Building`
- **Billing:** Stripe Checkout/Portal (mock fallback) → `Subscription` entitlements
- **Connectors:** `services/connectors` (`mock`, `bacnet_ip`, `modbus_tcp`, `honeywell_niagara`)
- **Safety:** HMAC `v2` validation tokens + write acknowledgement + FALLBACK on connector loss
- **Runtime:** API control plane; optional `python -m app.worker` with Redis lease

## Plans

| Plan | Buildings | Guarded write | Autonomous write | Connectors |
|------|-----------|---------------|------------------|------------|
| starter | 1 | no | no | mock, bacnet_ip |
| optimize | 5 | yes | no | + modbus, honeywell |
| autonomy | 25 | yes | yes (certified) | same |
| enterprise | 1000 | yes | yes | + custom + SSO |

## Onboarding path

1. Connect BMS adapter  
2. Map points  
3. Shadow mode (recommend only)  
4. Guarded pilot (human approve)  
5. Certification checklist  
6. Autonomy (requires `site_certified` + plan entitlement)

## Local demo

```bash
make setup
rm -f twinpilot.db services/api/twinpilot.db   # if upgrading schema
make demo
```

Login: `manager@twinpilot.demo` / `TwinPilot-Manager-Demo!`

## Production compose

```bash
export APP_ENV=production DEMO_MODE=false
export JWT_SECRET=... JWT_REFRESH_SECRET=... VALIDATION_TOKEN_SECRET=...
docker compose --profile production up --build
```

## Honeywell certification

See [HONEYWELL_CERTIFICATION.md](./HONEYWELL_CERTIFICATION.md).

## M&V honesty

ROI figures are labeled estimates until meter telemetry + IPMVP baseline are configured (`/settings/onboarding`).
