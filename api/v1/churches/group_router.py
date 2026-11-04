"""XynaFaith V2 Church Groups & Ministries API."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.core.church_dependencies import require_church_permission_dependency
from api.core.church_rbac import (
    PERMISSION_CHURCH_VIEW,
    PERMISSION_GROUPS_MANAGE,
)
from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.models.church_group import GROUP_STATUS_ACTIVE, ChurchGroup
from api.models.church_membership import ChurchMembership
from api.models.user import User
from api.schemas.church_group import (
    ChurchGroupCreate,
    ChurchGroupMemberCreate,
    ChurchGroupMemberUpdate,
)
from api.services.church_group_service import (
    ChurchGroupEntitlementRequired,
    ChurchGroupNotFound,
    ChurchGroupPermissionDenied,
    ChurchGroupValidationError,
    add_church_group_member,
    create_church_group,
    get_church_group,
    leave_church_group_member,
    list_church_group_members,
    update_church_group_member,
)


router = APIRouter()

church_view_required = require_church_permission_dependency(
    PERMISSION_CHURCH_VIEW
)

groups_manage_required = require_church_permission_dependency(
    PERMISSION_GROUPS_MANAGE
)


def _group_payload(group: ChurchGroup) -> dict:
    return {
        "id": group.id,
        "church_id": group.church_id,
        "name": group.name,
        "description": group.description,
        "group_type": group.group_type,
        "status": group.status,
        "created_at": group.created_at.isoformat(),
        "updated_at": group.updated_at.isoformat(),
    }


@router.get("/{church_id}/groups")
def list_church_groups(
    church_id: int,
    membership: ChurchMembership = Depends(church_view_required),
    db: Session = Depends(get_db),
):
    groups = (
        db.query(ChurchGroup)
        .filter(
            ChurchGroup.church_id == church_id,
            ChurchGroup.status == GROUP_STATUS_ACTIVE,
        )
        .order_by(
            ChurchGroup.name.asc(),
            ChurchGroup.id.asc(),
        )
        .all()
    )

    return {
        "church_id": membership.church_id,
        "groups": [_group_payload(group) for group in groups],
    }


@router.get("/{church_id}/groups/{group_id}")
def church_group_detail(
    church_id: int,
    group_id: int,
    membership: ChurchMembership = Depends(church_view_required),
    db: Session = Depends(get_db),
):
    try:
        group = get_church_group(
            db,
            church_id=church_id,
            group_id=group_id,
        )
    except ChurchGroupNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        ) from exc

    # Ordinary church members may only discover active groups.
    if (
        group.status != GROUP_STATUS_ACTIVE
        and membership.role not in {"owner", "admin", "pastor"}
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    return _group_payload(group)


@router.post(
    "/{church_id}/groups",
    status_code=status.HTTP_201_CREATED,
)
def create_group(
    church_id: int,
    payload: ChurchGroupCreate,
    _membership: ChurchMembership = Depends(groups_manage_required),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        group = create_church_group(
            db,
            user=current_user,
            church_id=church_id,
            name=payload.name,
            description=payload.description,
            group_type=payload.group_type,
        )

        db.commit()
        db.refresh(group)

        return _group_payload(group)

    except ChurchGroupNotFound as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Church Space not found",
        ) from exc

    except ChurchGroupPermissionDenied as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except ChurchGroupEntitlementRequired as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except ChurchGroupValidationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

def _group_membership_payload(group_membership) -> dict:
    return {
        "id": group_membership.id,
        "group_id": group_membership.group_id,
        "church_membership_id": (
            group_membership.church_membership_id
        ),
        "role": group_membership.role,
        "status": group_membership.status,
        "joined_at": (
            group_membership.joined_at.isoformat()
            if group_membership.joined_at
            else None
        ),
    }


@router.post(
    "/{church_id}/groups/{group_id}/members",
    status_code=status.HTTP_201_CREATED,
)
def add_group_member(
    church_id: int,
    group_id: int,
    payload: ChurchGroupMemberCreate,
    _membership: ChurchMembership = Depends(groups_manage_required),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        group_membership = add_church_group_member(
            db,
            user=current_user,
            church_id=church_id,
            group_id=group_id,
            church_membership_id=payload.church_membership_id,
            role=payload.role,
        )

        db.commit()
        db.refresh(group_membership)

        return _group_membership_payload(group_membership)

    except ChurchGroupNotFound as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ChurchGroupPermissionDenied as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except ChurchGroupEntitlementRequired as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except ChurchGroupValidationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get(
    "/{church_id}/groups/{group_id}/members",
)
def list_group_members(
    church_id: int,
    group_id: int,
    _membership: ChurchMembership = Depends(church_view_required),
    db: Session = Depends(get_db),
):
    try:
        memberships = list_church_group_members(
            db,
            church_id=church_id,
            group_id=group_id,
        )

        return {
            "church_id": church_id,
            "group_id": group_id,
            "members": [
                _group_membership_payload(item)
                for item in memberships
            ],
        }

    except ChurchGroupNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        ) from exc


@router.patch(
    "/{church_id}/groups/{group_id}/members/{group_membership_id}",
)
def update_group_member(
    church_id: int,
    group_id: int,
    group_membership_id: int,
    payload: ChurchGroupMemberUpdate,
    _membership: ChurchMembership = Depends(groups_manage_required),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        group_membership = update_church_group_member(
            db,
            user=current_user,
            church_id=church_id,
            group_id=group_id,
            group_membership_id=group_membership_id,
            role=payload.role,
            member_status=payload.status,
        )

        db.commit()
        db.refresh(group_membership)

        return _group_membership_payload(group_membership)

    except ChurchGroupNotFound as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except (
        ChurchGroupPermissionDenied,
        ChurchGroupEntitlementRequired,
    ) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except ChurchGroupValidationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{church_id}/groups/{group_id}/members/{group_membership_id}",
)
def remove_group_member(
    church_id: int,
    group_id: int,
    group_membership_id: int,
    _membership: ChurchMembership = Depends(groups_manage_required),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        group_membership = leave_church_group_member(
            db,
            user=current_user,
            church_id=church_id,
            group_id=group_id,
            group_membership_id=group_membership_id,
        )

        db.commit()
        db.refresh(group_membership)

        return _group_membership_payload(group_membership)

    except ChurchGroupNotFound as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except (
        ChurchGroupPermissionDenied,
        ChurchGroupEntitlementRequired,
    ) as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except ChurchGroupValidationError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
