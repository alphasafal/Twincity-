"""FastAPI dependencies for auth, RBAC, and tenancy."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models import Building, Membership, Organization, User
from app.models.enums import UserRole
from app.services.tenancy import accessible_buildings, get_membership, user_can_access_building

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
    "org_manage": {UserRole.ADMINISTRATOR, UserRole.FACILITY_MANAGER},
    "billing_manage": {UserRole.ADMINISTRATOR},
    "connector_manage": {UserRole.ADMINISTRATOR, UserRole.FACILITY_MANAGER},
    "site_certify": {UserRole.ADMINISTRATOR, UserRole.FACILITY_MANAGER},
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
    # Stash org claim for downstream handlers
    user._token_org_id = payload.get("org_id")  # type: ignore[attr-defined]
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


def get_building_for_user(building_id: str, db: Session, user: User) -> Building:
    building = db.get(Building, building_id)
    if building is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Building not found")
    if not user_can_access_building(db, user, building):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to building")
    return building


def require_building_access(building_id: str) -> Callable[..., Building]:
    def checker(
        db: Annotated[Session, Depends(get_db)],
        user: Annotated[User, Depends(get_current_user)],
    ) -> Building:
        return get_building_for_user(building_id, db, user)

    return checker


def get_organization_for_user(organization_id: str, db: Session, user: User) -> Organization:
    org = db.get(Organization, organization_id)
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    membership = get_membership(db, user, organization_id)
    if membership is None and UserRole(user.role) != UserRole.ADMINISTRATOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No access to organization")
    return org


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]


def optional_service_token(
    x_telemetry_token: Annotated[str | None, Header()] = None,
) -> str | None:
    return x_telemetry_token


def list_accessible_buildings(db: Session, user: User) -> list[Building]:
    return accessible_buildings(db, user)
