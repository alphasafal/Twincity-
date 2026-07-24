"""TwinPilot FastAPI application entrypoint."""

from __future__ import annotations

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api.v1.platform import router as platform_router
from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.security import decode_token
from app.db.seed import seed_database
from app.db.session import Base, SessionLocal, engine
from app.models import User
from app.services.runtime import hub
from app.services.tenancy import user_can_access_building

settings = get_settings()
logger = logging.getLogger("twinpilot.api")
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s","message":"%(message)s"}',
)

_METRICS = {
    "http_requests_total": 0,
    "http_errors_total": 0,
    "ws_connections_total": 0,
}


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        _METRICS["http_requests_total"] += 1
        if response.status_code >= 500:
            _METRICS["http_errors_total"] += 1
        duration_ms = (time.perf_counter() - started) * 1000
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%.1f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            request_id,
        )
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.validate_production_secrets()
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if settings.seed_on_startup and (settings.demo_mode or not settings.is_production):
            building = seed_database(db)
        else:
            from sqlalchemy import select
            from app.models import Building

            building = db.scalar(select(Building).limit(1))
            if building is None:
                raise RuntimeError("No buildings found and seed_on_startup disabled")
        hub.initialize_from_db(db, building)
    finally:
        db.close()

    # Control loop may run in API process (demo) or dedicated worker (production)
    if settings.control_loop_enabled and settings.run_control_loop_in_api and not settings.worker_mode:
        await hub.start_background()
        for _ in range(3):
            await hub.run_cycle()
    yield
    await hub.stop_background()


app = FastAPI(
    title="TwinPilot API",
    description="Verifiable Autonomous Building Optimization — multi-tenant production platform",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIdMiddleware)
app.include_router(v1_router)
app.include_router(platform_router)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "api",
        "demo_mode": settings.demo_mode,
        "app_env": settings.app_env,
        "simulator": hub.simulator.health(),
        "components": hub.service_health,
        "control_loop_in_api": settings.run_control_loop_in_api and not settings.worker_mode,
    }


@app.get("/ready")
def ready() -> dict:
    ready_ok = hub.building_id is not None and hub.latest_state
    return {"ready": bool(ready_ok), "building_id": hub.building_id}


@app.get("/metrics")
def metrics() -> PlainTextResponse:
    if not settings.metrics_enabled:
        return PlainTextResponse("# metrics disabled\n", media_type="text/plain")
    lines = [
        "# HELP twinpilot_http_requests_total Total HTTP requests",
        "# TYPE twinpilot_http_requests_total counter",
        f"twinpilot_http_requests_total {_METRICS['http_requests_total']}",
        "# HELP twinpilot_http_errors_total Total HTTP 5xx responses",
        "# TYPE twinpilot_http_errors_total counter",
        f"twinpilot_http_errors_total {_METRICS['http_errors_total']}",
        "# HELP twinpilot_ws_connections_total Total websocket connections accepted",
        "# TYPE twinpilot_ws_connections_total counter",
        f"twinpilot_ws_connections_total {_METRICS['ws_connections_total']}",
    ]
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")


@app.websocket("/ws/buildings/{building_id}")
async def building_ws(
    websocket: WebSocket,
    building_id: str,
    token: str | None = Query(default=None),
) -> None:
    # Authenticate before accepting when required
    if settings.require_ws_auth or settings.is_production or not settings.demo_mode:
        raw = token or websocket.query_params.get("access_token")
        if not raw:
            auth = websocket.headers.get("authorization") or ""
            if auth.lower().startswith("bearer "):
                raw = auth.split(" ", 1)[1]
        if not raw:
            await websocket.close(code=4401)
            return
        db = SessionLocal()
        try:
            try:
                payload = decode_token(raw)
            except ValueError:
                await websocket.close(code=4401)
                return
            user = db.get(User, payload.get("sub"))
            if user is None or not user.is_active:
                await websocket.close(code=4401)
                return
            from app.models import Building

            building = db.get(Building, building_id)
            if building is None or not user_can_access_building(db, user, building):
                await websocket.close(code=4403)
                return
        finally:
            db.close()

    await websocket.accept()
    _METRICS["ws_connections_total"] += 1
    queue = hub.subscribe()
    try:
        await websocket.send_json(
            {
                "event_type": "telemetry.updated",
                "event_id": str(uuid.uuid4()),
                "building_id": building_id,
                "timestamp": hub.latest_state.get("timestamp_iso"),
                "payload": {"state": hub.latest_state},
                "schema_version": "1.0",
            }
        )
        while True:
            event = await queue.get()
            if event.get("building_id") and event["building_id"] != building_id:
                continue
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    finally:
        hub.unsubscribe(queue)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
            "error_type": type(exc).__name__ if settings.demo_mode else None,
        },
    )
