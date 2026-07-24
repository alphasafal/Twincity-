# Honeywell Niagara / Forge adapter — certification checklist

TwinPilot is an optimization + safety layer **on top of** Honeywell BMS, not a BMS replacement.

## Adapter

- Package: `twinpilot_connectors.adapters.honeywell_niagara`
- Type code: `honeywell_niagara`
- Protocols: `TelemetrySource` + `ActuatorSink`
- Secrets: store via `secret_ref` / env vault — never plaintext passwords in DB

## Sandbox harness

1. Provision connector with `transport=simulated` (default)  
2. Discover points → map cooling setpoints as `readwrite`  
3. Run shadow mode ≥ configured days  
4. Guarded pilot with human approve/apply  
5. Inject connector offline → confirm FALLBACK + no writes  
6. Complete site certification checklist  
7. Enable autonomy only on `autonomy`/`enterprise` plan

## Live station

```json
{
  "transport": "live",
  "base_url": "https://niagara.customer.example",
  "station": "BuildingA",
  "api_key": "<from vault>",
  "verify_tls": true
}
```

## Required evidence pack

- [ ] Point map export  
- [ ] Write-ack samples (requested vs readback)  
- [ ] Fail-safe drill log  
- [ ] Immutable audit export  
- [ ] M&V baseline configured  
- [ ] Customer sign-off on autonomy
