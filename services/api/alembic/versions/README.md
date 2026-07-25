# Alembic versions

Runtime demo boot uses `Base.metadata.create_all` in the FastAPI lifespan, so this folder may be empty until you generate a revision:

```bash
cd services/api
alembic revision --autogenerate -m "initial"
alembic upgrade head
```

Keep migrations aligned with `app.models.entities`.
