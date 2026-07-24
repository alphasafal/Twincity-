# Deployment

TwinPilot is packaged for **local demos** and lightweight Docker Compose. It is **not** a production-certified building control deployment guide.

---

## Local (recommended for demos)

```bash
make setup
make demo
```

| Service | URL |
|---------|-----|
| Web | http://localhost:3000 |
| API | http://localhost:8000 |
| OpenAPI | http://localhost:8000/docs |

SQLite file defaults to `services/api/twinpilot.db` (or `/data/twinpilot.db` in containers). **Redis is not required.**

---

## Docker Compose profiles

```bash
# Demo: api + web, SQLite volume, no Redis
docker compose --profile demo up --build

# Full: adds optional Postgres (set DATABASE_URL to use it)
DATABASE_URL=postgresql+psycopg://twinpilot:twinpilot@postgres:5432/twinpilot \
  docker compose --profile full up --build

# EnergyPlus profile: same services; mount/configure EnergyPlus env
docker compose --profile energyplus up --build
```

Images:

- `infrastructure/docker/Dockerfile.api`
- `infrastructure/docker/Dockerfile.web`

---

## Environment

Copy `.env.example` → `.env`. Critical for any shared host:

- Rotate `JWT_SECRET` / `JWT_REFRESH_SECRET`
- Set `DEMO_MODE=false` only if you understand auth/ingest implications
- Pin `CORS_ORIGINS` / `WEB_ORIGIN`
- Keep demo passwords out of non-demo environments

Frontend build arg: `NEXT_PUBLIC_API_URL` must reach the API from the **browser**.

---

## Optional sidecars

| Component | How |
|-----------|-----|
| Ollama | Run on host; `AGENT_PROVIDER=ollama`, `OLLAMA_BASE_URL` |
| MCP | `python -m twinpilot_mcp` with API reachable |
| EnergyPlus | Host install + env paths; see [ENERGYPLUS.md](ENERGYPLUS.md) |

---

## Scaling / HA (out of scope)

The control loop and WebSocket hub are **in-process** inside the API worker. Multi-replica API without sticky sessions / external pub-sub will diverge. Postgres is available via the `full` profile, but the demo does not ship Redis, Celery, or Kubernetes manifests.

---

## Security reminders

- Demo credentials are public in the README — **dev only**
- No production BMS credentials should be placed in this stack
- Not certified for unsupervised live-building control
