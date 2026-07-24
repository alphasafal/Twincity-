"""TwinPilot FastAPI application entrypoint."""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.db.seed import seed_database
from app.db.session import Base, SessionLocal, engine
from app.services.runtime import hub

settings = get_settings()


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "same-origin"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        building = seed_database(db)
        hub.initialize_from_db(db, building)
    finally:
        db.close()
    await hub.start_background()
    # Prime a few cycles so dashboards have history quickly
    for _ in range(3):
        await hub.run_cycle()
    yield
    await hub.stop_background()


app = FastAPI(
    title="TwinPilot API",
    description="Verifiable Autonomous Building Optimization",
    version="0.1.0",
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


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "api",
        "demo_mode": settings.demo_mode,
        "simulator": hub.simulator.health(),
        "components": hub.service_health,
    }


@app.get("/ready")
def ready() -> dict:
    ready_ok = hub.building_id is not None and hub.latest_state
    return {"ready": bool(ready_ok), "building_id": hub.building_id}


@app.websocket("/ws/buildings/{building_id}")
async def building_ws(websocket: WebSocket, building_id: str) -> None:
    await websocket.accept()
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
            # Avoid leaking internals in non-demo; demo surfaces type for DX
            "error_type": type(exc).__name__ if settings.demo_mode else None,
        },
    )
