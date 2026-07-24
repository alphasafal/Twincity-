"""Simple in-process sliding-window rate limiter for auth and assistant."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.config import get_settings


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, *, limit: int, window_seconds: int = 60) -> None:
        now = time.monotonic()
        with self._lock:
            bucket = self._hits[key]
            cutoff = now - window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded ({limit}/{window_seconds}s). Retry shortly.",
                    headers={"Retry-After": str(window_seconds)},
                )
            bucket.append(now)


limiter = SlidingWindowRateLimiter()


def client_key(request: Request, suffix: str) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    ip = (forwarded.split(",")[0].strip() if forwarded else None) or (
        request.client.host if request.client else "unknown"
    )
    return f"{suffix}:{ip}"


def enforce_auth_rate_limit(request: Request) -> None:
    settings = get_settings()
    limiter.check(
        client_key(request, "auth"),
        limit=settings.rate_limit_auth_per_minute,
        window_seconds=60,
    )


def enforce_assistant_rate_limit(request: Request) -> None:
    settings = get_settings()
    limiter.check(
        client_key(request, "assistant"),
        limit=settings.rate_limit_assistant_per_minute,
        window_seconds=60,
    )
