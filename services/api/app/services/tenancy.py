"""Organization membership and building access helpers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Building, Membership, Organization, User
from app.models.enums import UserRole


def list_user_memberships(db: Session, user: User) -> list[Membership]:
    return list(
        db.scalars(
            select(Membership).where(
                Membership.user_id == user.id,
                Membership.is_active.is_(True),
            )
        ).all()
    )


def list_user_organizations(db: Session, user: User) -> list[Organization]:
    memberships = list_user_memberships(db, user)
    if not memberships:
        return []
    org_ids = [m.organization_id for m in memberships]
    return list(db.scalars(select(Organization).where(Organization.id.in_(org_ids))).all())


def get_membership(db: Session, user: User, organization_id: str) -> Membership | None:
    return db.scalar(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.organization_id == organization_id,
            Membership.is_active.is_(True),
        )
    )


def user_can_access_building(db: Session, user: User, building: Building) -> bool:
    if UserRole(user.role) == UserRole.ADMINISTRATOR and building.is_demo:
        # Demo administrators may access the sandbox building even before membership hydrate
        if building.organization_id is None:
            return True
    if building.organization_id is None:
        # Legacy unscoped buildings: only active demo admins
        return UserRole(user.role) == UserRole.ADMINISTRATOR
    return get_membership(db, user, building.organization_id) is not None


def accessible_buildings(db: Session, user: User) -> list[Building]:
    memberships = list_user_memberships(db, user)
    if not memberships:
        # Back-compat: if no memberships yet, demo admin sees all demo buildings
        if UserRole(user.role) == UserRole.ADMINISTRATOR:
            return list(db.scalars(select(Building)).all())
        return []
    org_ids = [m.organization_id for m in memberships]
    return list(db.scalars(select(Building).where(Building.organization_id.in_(org_ids))).all())


def require_org_admin(membership: Membership | None, user: User) -> None:
    from fastapi import HTTPException, status

    if UserRole(user.role) == UserRole.ADMINISTRATOR:
        return
    if membership is None or membership.org_role not in {
        UserRole.ADMINISTRATOR.value,
        UserRole.FACILITY_MANAGER.value,
    }:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Org admin required")
