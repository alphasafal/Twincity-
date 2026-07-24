"""JWT auth and password hashing."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta
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


def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_token(
    subject: str,
    *,
    token_type: str,
    expires_delta: timedelta,
    secret: str,
    extra: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
        "jti": secrets.token_hex(8),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def create_access_token(
    user_id: str,
    *,
    org_id: str | None = None,
    org_role: str | None = None,
) -> str:
    settings = get_settings()
    extra: dict[str, Any] = {}
    if org_id:
        extra["org_id"] = org_id
    if org_role:
        extra["org_role"] = org_role
    return create_token(
        user_id,
        token_type="access",
        expires_delta=timedelta(minutes=settings.jwt_access_minutes),
        secret=settings.jwt_secret,
        extra=extra or None,
    )


def create_refresh_token(user_id: str, *, org_id: str | None = None) -> str:
    settings = get_settings()
    extra = {"org_id": org_id} if org_id else None
    return create_token(
        user_id,
        token_type="refresh",
        expires_delta=timedelta(days=settings.jwt_refresh_days),
        secret=settings.jwt_refresh_secret,
        extra=extra,
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


def sign_hmac(payload: str, secret: str | None = None) -> str:
    settings = get_settings()
    key = (secret or settings.validation_token_secret).encode("utf-8")
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_hmac(payload: str, signature: str, secret: str | None = None) -> bool:
    expected = sign_hmac(payload, secret=secret)
    return hmac.compare_digest(expected, signature)
