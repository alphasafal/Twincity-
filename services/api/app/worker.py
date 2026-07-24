"""Per-building control-loop worker process.

Production deployment runs this separately from the API so the control plane
can scale independently. Coordination uses Redis leases when available.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import uuid
from datetime import UTC, datetime

from sqlalchemy import select

from app.core.config import get_settings
from app.db.seed import seed_database
from app.db.session import Base, SessionLocal, engine
from app.models import Building
from app.services.runtime import hub

logger = logging.getLogger("twinpilot.worker")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


class RedisLease:
    def __init__(self, redis_url: str, key: str, owner: str, ttl: int = 30) -> None:
        self.redis_url = redis_url
        self.key = key
        self.owner = owner
        self.ttl = ttl
        self._client = None

    def connect(self):
        try:
            import redis  # type: ignore

            self._client = redis.Redis.from_url(self.redis_url, decode_responses=True)
            self._client.ping()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Redis unavailable (%s) — running without distributed lease", exc)
            self._client = None
            return False

    def acquire(self) -> bool:
        if self._client is None:
            return True
        return bool(self._client.set(self.key, self.owner, nx=True, ex=self.ttl))

    def refresh(self) -> bool:
        if self._client is None:
            return True
        current = self._client.get(self.key)
        if current == self.owner:
            self._client.expire(self.key, self.ttl)
            return True
        return self.acquire()

    def release(self) -> None:
        if self._client is None:
            return
        if self._client.get(self.key) == self.owner:
            self._client.delete(self.key)


async def run_worker() -> None:
    settings = get_settings()
    settings.validate_production_secrets()
    Base.metadata.create_all(bind=engine)

    owner = f"worker-{uuid.uuid4().hex[:8]}"
    db = SessionLocal()
    try:
        if settings.seed_on_startup and settings.demo_mode:
            building = seed_database(db)
        else:
            building = db.scalar(select(Building).limit(1))
            if building is None:
                raise RuntimeError("No building available for worker")
        hub.initialize_from_db(db, building)
        building_id = building.id
    finally:
        db.close()

    lease = RedisLease(
        settings.redis_url,
        key=f"twinpilot:lease:building:{building_id}",
        owner=owner,
        ttl=max(15, settings.control_interval_seconds * 3),
    )
    lease.connect()

    stop = asyncio.Event()

    def _stop(*_args):
        stop.set()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)

    logger.info("Worker %s starting for building %s", owner, building_id)
    while not stop.is_set():
        if lease.refresh():
            try:
                await hub.run_cycle()
            except Exception:  # noqa: BLE001
                logger.exception("Control cycle failed at %s", datetime.now(UTC).isoformat())
        else:
            logger.info("Lease held by another worker — idle")
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.control_interval_seconds)
        except TimeoutError:
            pass
    lease.release()
    logger.info("Worker %s stopped", owner)


def main() -> None:
    os.environ.setdefault("WORKER_MODE", "true")
    os.environ.setdefault("RUN_CONTROL_LOOP_IN_API", "false")
    get_settings.cache_clear()
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
