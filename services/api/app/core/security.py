"""JWT auth and password hashing."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_token(subject: str, *, token_type: str, expires_delta: timedelta, secret: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    return create_token(
        user_id,
        token_type="access",
        expires_delta=timedelta(minutes=settings.jwt_access_minutes),
        secret=settings.jwt_secret,
    )


def create_refresh_token(user_id: str) -> str:
    settings = get_settings()
    return create_token(
        user_id,
        token_type="refresh",
        expires_delta=timedelta(days=settings.jwt_refresh_days),
        secret=settings.jwt_refresh_secret,
    )


def decode_token(token: str, *, refresh: bool = False) -> dict[str, Any]:
    settings = get_settings()
    secret = settings.jwt_refresh_secret if refresh else settings.jwt_secret
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    expected = "refresh" if refresh else "access"
    if payload.get("type") != expected:
        raise ValueError("Unexpected token type")
    return payload
