#!/usr/bin/env bash
# Ensure demo seed data exists. Prefer live API; fall back to direct seed.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/.venv/bin/activate" 2>/dev/null || true

API_URL="${TWINPILOT_API_URL:-http://localhost:8000}"

if curl -sf "$API_URL/health" >/dev/null 2>&1; then
  echo "API is running — seed already applied on startup (create_all + seed_database)."
  echo "Demo users (dev only):"
  echo "  admin@twinpilot.demo / TwinPilot-Admin-Demo!"
  echo "  manager@twinpilot.demo / TwinPilot-Manager-Demo!"
  echo "  operator@twinpilot.demo / TwinPilot-Operator-Demo!"
  echo "  viewer@twinpilot.demo / TwinPilot-Viewer-Demo!"
  exit 0
fi

echo "API not reachable at $API_URL — seeding SQLite database directly."
cd "$ROOT/services/api"
export PYTHONPATH="$ROOT/services/api${PYTHONPATH:+:$PYTHONPATH}"
python - <<'PY'
from app.db.session import Base, SessionLocal, engine
from app.db.seed import seed_database, DEMO_USERS

Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    building = seed_database(db)
    db.commit()
    print(f"Seeded building: {building.name} ({building.id})")
    print("Demo users:")
    for u in DEMO_USERS:
        print(f"  {u['email']} / {u['password']}  [{u['role']}]")
finally:
    db.close()
PY
