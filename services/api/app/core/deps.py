"""FastAPI dependencies for auth and RBAC."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models import User
from app.models.enums import UserRole

bearer = HTTPBearer(auto_error=False)

ROLE_ORDER = {
    UserRole.VIEWER: 1,
    UserRole.OPERATOR: 2,
    UserRole.FACILITY_MANAGER: 3,
    UserRole.ADMINISTRATOR: 4,
}

PERMISSIONS = {
    "mode_change": {UserRole.ADMINISTRATOR},
    "plan_approve_high": {UserRole.ADMINISTRATOR, UserRole.FACILITY_MANAGER},
    "plan_approve_low": {
        UserRole.ADMINISTRATOR,
        UserRole.FACILITY_MANAGER,
        UserRole.OPERATOR,
    },
    "plan_execute": {UserRole.ADMINISTRATOR, UserRole.FACILITY_MANAGER},
    "manual_override": {UserRole.ADMINISTRATOR, UserRole.FACILITY_MANAGER, UserRole.OPERATOR},
    "rollback": {UserRole.ADMINISTRATOR, UserRole.FACILITY_MANAGER, UserRole.OPERATOR},
    "constraint_modify": {UserRole.ADMINISTRATOR},
    "user_manage": {UserRole.ADMINISTRATOR},
    "simulation_run": {UserRole.ADMINISTRATOR, UserRole.FACILITY_MANAGER},
}


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "unknown")


def get_current_user(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if creds is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(creds.credentials)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    user = db.get(User, payload["sub"])
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")
    return user


def require_permission(permission: str) -> Callable[[User], User]:
    allowed = PERMISSIONS.get(permission, set())

    def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        role = UserRole(user.role)
        if role not in allowed and role != UserRole.ADMINISTRATOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return user

    return checker


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    allowed = set(roles)

    def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if UserRole(user.role) not in allowed and UserRole(user.role) != UserRole.ADMINISTRATOR:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return checker


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


def optional_service_token(
    x_telemetry_token: Annotated[str | None, Header()] = None,
) -> str | None:
    return x_telemetry_token
