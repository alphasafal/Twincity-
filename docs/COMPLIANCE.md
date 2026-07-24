# TwinPilot compliance pack (SOC2-oriented)

## Role matrix

| Capability | Viewer | Operator | Facility Manager | Administrator |
|------------|--------|----------|------------------|---------------|
| Read telemetry | ✓ | ✓ | ✓ | ✓ |
| Approve low-risk plans | | ✓ | ✓ | ✓ |
| Apply / execute | | | ✓ | ✓ |
| Mode change | | | | ✓ |
| Connector manage | | | ✓ | ✓ |
| Billing | | | | ✓ |
| Org invite | | | ✓ | ✓ |
| Site certify | | | ✓ | ✓ |

## Audit

- `AuditEvent.immutable = true`
- Org export: `GET /api/v1/organizations/{id}/audit/export`
- Retain exports per customer DPA (default recommendation: 1 year online, 7 years cold)

## Incident runbook (connector / write failure)

1. Safety Shield or actuation sets `FALLBACK`  
2. Alert `connector_offline` or `write_ack_failed` opened  
3. Further writes blocked until connector healthy + operator clears mode  
4. Export audit + write acknowledgements for RCA

## Secrets

- Production rejects default JWT / validation secrets when `APP_ENV=production`
- `DEMO_MODE` must be false in production
- Connector secrets via `secret_ref` (`env:` / KMS), not DB plaintext
