from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from api.core.church_dependencies import require_church_permission_dependency
from api.core.church_rbac import (
    PERMISSION_CHURCH_VIEW,
    PERMISSION_MEMBERS_VIEW,
    ROLE_PERMISSIONS,
)
from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.models.church import Church
from api.models.church_membership import ChurchMembership
from api.models.user import User
from api.services.church_membership_service import get_primary_church_membership


router = APIRouter(prefix="/churches", tags=["Church Spaces"])


church_view_required = require_church_permission_dependency(
    PERMISSION_CHURCH_VIEW
)

members_view_required = require_church_permission_dependency(
    PERMISSION_MEMBERS_VIEW
)


def _permissions_for_membership(
    membership: ChurchMembership,
) -> list[str]:
    return sorted(ROLE_PERMISSIONS.get(membership.role, frozenset()))


def _church_payload(church: Church) -> dict:
    return {
        "id": church.id,
        "name": church.name,
        "location": church.location,
        "denomination": church.denomination,
        "country": church.country,
        "city": church.city,
        "is_featured": bool(church.is_featured),
        "is_verified": bool(church.is_verified),
    }


def _membership_payload(membership: ChurchMembership) -> dict:
    return {
        "id": membership.id,
        "church_id": membership.church_id,
        "user_id": membership.user_id,
        "role": membership.role,
        "status": membership.status,
        "is_primary": bool(membership.is_primary),
        "joined_at": (
            membership.joined_at.isoformat()
            if membership.joined_at
            else None
        ),
    }


def _space_payload(
    church: Church,
    membership: ChurchMembership,
) -> dict:
    permissions = _permissions_for_membership(membership)

    return {
        "church": _church_payload(church),
        "membership": _membership_payload(membership),
        "permissions": permissions,
        "capabilities": {
            "can_manage_church": "church.manage" in permissions,
            "can_view_members": "members.view" in permissions,
            "can_manage_members": "members.manage" in permissions,
            "can_create_content": "content.create" in permissions,
            "can_manage_content": "content.manage" in permissions,
            "can_view_prayer": "prayer.view" in permissions,
            "can_manage_pastoral_care": (
                "pastoral_care.manage" in permissions
            ),
            "can_view_analytics": "analytics.view" in permissions,
        },
    }


@router.get("/mine")
def my_church_space(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = get_primary_church_membership(
        db,
        user_id=current_user.id,
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No primary Church Space found",
        )

    church = db.get(Church, membership.church_id)

    if church is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Church Space not found",
        )

    return _space_payload(church, membership)


@router.get("/{church_id}/space")
def church_space(
    church_id: int,
    membership: ChurchMembership = Depends(church_view_required),
    db: Session = Depends(get_db),
):
    church = db.get(Church, church_id)

    if church is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Church Space not found",
        )

    return _space_payload(church, membership)


@router.get("/{church_id}/members")
def church_members(
    church_id: int,
    _: ChurchMembership = Depends(members_view_required),
    db: Session = Depends(get_db),
):
    memberships = (
        db.query(ChurchMembership)
        .options(joinedload(ChurchMembership.user))
        .filter(
            ChurchMembership.church_id == church_id,
            ChurchMembership.status == "active",
        )
        .order_by(
            ChurchMembership.is_primary.desc(),
            ChurchMembership.joined_at.asc(),
            ChurchMembership.id.asc(),
        )
        .all()
    )

    members = []

    for membership in memberships:
        user = membership.user

        members.append(
            {
                "membership_id": membership.id,
                "user_id": membership.user_id,
                "role": membership.role,
                "status": membership.status,
                "is_primary": bool(membership.is_primary),
                "joined_at": (
                    membership.joined_at.isoformat()
                    if membership.joined_at
                    else None
                ),
                "user": {
                    "id": user.id,
                    "name": getattr(user, "name", None),
                },
            }
        )

    return {
        "church_id": church_id,
        "members": members,
        "count": len(members),
    }
