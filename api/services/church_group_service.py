"""Authoritative XynaFaith V2 Church Groups service."""

from sqlalchemy.orm import Session

from api.core.church_rbac import (
    MEMBERSHIP_STATUS_ACTIVE,
    PERMISSION_GROUPS_MANAGE,
)
from api.core.entitlements import ENTITLEMENT_CHURCH_GROUPS
from api.models.church_group import (
    GROUP_MEMBER_ROLES,
    GROUP_MEMBER_STATUSES,
    GROUP_MEMBER_STATUS_ACTIVE,
    GROUP_MEMBER_STATUS_LEFT,
    GROUP_STATUS_ACTIVE,
    GROUP_TYPES,
    ChurchGroup,
    ChurchGroupMembership,
)
from api.models.church_membership import ChurchMembership
from api.models.user import User
from api.services.church_membership_service import (
    ChurchMembershipInactive,
    ChurchMembershipNotFound,
    ChurchPermissionDenied,
    require_church_permission,
)
from api.services.effective_access_service import has_entitlement


class ChurchGroupError(Exception):
    """Base error for Church Group operations."""


class ChurchGroupNotFound(ChurchGroupError):
    """Requested group is not available in the trusted Church Space."""


class ChurchGroupPermissionDenied(ChurchGroupError):
    """Group mutation is not authorized."""


class ChurchGroupEntitlementRequired(ChurchGroupError):
    """Church plan does not grant Groups & Ministries."""


class ChurchGroupValidationError(ChurchGroupError):
    """Group input is invalid."""


def _require_group_management(
    db: Session,
    *,
    user: User,
    church_id: int,
) -> None:
    try:
        require_church_permission(
            db,
            church_id=church_id,
            user_id=user.id,
            permission=PERMISSION_GROUPS_MANAGE,
        )
    except ChurchMembershipNotFound as exc:
        raise ChurchGroupNotFound("Church Space not found") from exc
    except ChurchMembershipInactive as exc:
        raise ChurchGroupPermissionDenied(
            "Church membership is not active"
        ) from exc
    except ChurchPermissionDenied as exc:
        raise ChurchGroupPermissionDenied(
            "Insufficient Church Space permission"
        ) from exc

    if not has_entitlement(
        db,
        user,
        ENTITLEMENT_CHURCH_GROUPS,
        church_id=church_id,
    ):
        raise ChurchGroupEntitlementRequired(
            "Church Groups & Ministries are not available"
        )


def create_church_group(
    db: Session,
    *,
    user: User,
    church_id: int,
    name: str,
    description: str | None,
    group_type: str,
) -> ChurchGroup:
    _require_group_management(
        db,
        user=user,
        church_id=church_id,
    )

    normalized_name = name.strip()
    normalized_description = (
        description.strip()
        if description is not None and description.strip()
        else None
    )
    normalized_type = group_type.strip()

    if not normalized_name or len(normalized_name) > 200:
        raise ChurchGroupValidationError("Group name is invalid")

    if normalized_type not in GROUP_TYPES:
        raise ChurchGroupValidationError("Group type is invalid")

    existing = (
        db.query(ChurchGroup)
        .filter(
            ChurchGroup.church_id == church_id,
            ChurchGroup.name == normalized_name,
        )
        .one_or_none()
    )

    if existing is not None:
        raise ChurchGroupValidationError(
            "A group with this name already exists"
        )

    group = ChurchGroup(
        church_id=church_id,
        name=normalized_name,
        description=normalized_description,
        group_type=normalized_type,
        status=GROUP_STATUS_ACTIVE,
    )

    db.add(group)
    db.flush()

    return group


def get_church_group(
    db: Session,
    *,
    church_id: int,
    group_id: int,
) -> ChurchGroup:
    group = (
        db.query(ChurchGroup)
        .filter(
            ChurchGroup.id == group_id,
            ChurchGroup.church_id == church_id,
        )
        .one_or_none()
    )

    if group is None:
        raise ChurchGroupNotFound("Group not found")

    return group


def add_church_group_member(
    db: Session,
    *,
    user: User,
    church_id: int,
    group_id: int,
    church_membership_id: int,
    role: str,
) -> ChurchGroupMembership:
    """Add one Church member to a group within the same Church Space."""

    _require_group_management(
        db,
        user=user,
        church_id=church_id,
    )

    group = get_church_group(
        db,
        church_id=church_id,
        group_id=group_id,
    )

    if group.status != GROUP_STATUS_ACTIVE:
        raise ChurchGroupValidationError(
            "Members cannot be added to an inactive or archived group"
        )

    if role not in GROUP_MEMBER_ROLES:
        raise ChurchGroupValidationError(
            "Group member role is invalid"
        )

    church_membership = (
        db.query(ChurchMembership)
        .filter(
            ChurchMembership.id == church_membership_id,
            ChurchMembership.church_id == church_id,
        )
        .one_or_none()
    )

    if church_membership is None:
        # Fail closed for a membership belonging to another Church.
        raise ChurchGroupNotFound(
            "Church member not found"
        )

    if church_membership.status != MEMBERSHIP_STATUS_ACTIVE:
        raise ChurchGroupValidationError(
            "Church member is not active"
        )

    existing = (
        db.query(ChurchGroupMembership)
        .filter(
            ChurchGroupMembership.group_id == group.id,
            ChurchGroupMembership.church_membership_id
            == church_membership.id,
        )
        .one_or_none()
    )

    if existing is not None:
        raise ChurchGroupValidationError(
            "Church member already belongs to this group"
        )

    group_membership = ChurchGroupMembership(
        group_id=group.id,
        church_membership_id=church_membership.id,
        role=role,
        status=GROUP_MEMBER_STATUS_ACTIVE,
    )

    db.add(group_membership)
    db.flush()

    return group_membership


def list_church_group_members(
    db: Session,
    *,
    church_id: int,
    group_id: int,
) -> list[ChurchGroupMembership]:
    """List memberships for one group scoped to its Church Space."""

    group = get_church_group(
        db,
        church_id=church_id,
        group_id=group_id,
    )

    return (
        db.query(ChurchGroupMembership)
        .filter(
            ChurchGroupMembership.group_id == group.id,
            ChurchGroupMembership.status != GROUP_MEMBER_STATUS_LEFT,
        )
        .order_by(
            ChurchGroupMembership.role.asc(),
            ChurchGroupMembership.id.asc(),
        )
        .all()
    )


def get_church_group_membership(
    db: Session,
    *,
    church_id: int,
    group_id: int,
    group_membership_id: int,
) -> ChurchGroupMembership:
    """Resolve a group membership without crossing Church boundaries."""

    group = get_church_group(
        db,
        church_id=church_id,
        group_id=group_id,
    )

    group_membership = (
        db.query(ChurchGroupMembership)
        .filter(
            ChurchGroupMembership.id == group_membership_id,
            ChurchGroupMembership.group_id == group.id,
        )
        .one_or_none()
    )

    if group_membership is None:
        raise ChurchGroupNotFound("Group member not found")

    return group_membership


def update_church_group_member(
    db: Session,
    *,
    user: User,
    church_id: int,
    group_id: int,
    group_membership_id: int,
    role: str | None = None,
    member_status: str | None = None,
) -> ChurchGroupMembership:
    """Update a group member's group-specific role or lifecycle status."""

    _require_group_management(
        db,
        user=user,
        church_id=church_id,
    )

    group_membership = get_church_group_membership(
        db,
        church_id=church_id,
        group_id=group_id,
        group_membership_id=group_membership_id,
    )

    if role is None and member_status is None:
        raise ChurchGroupValidationError(
            "At least one group membership field must be provided"
        )

    if role is not None:
        normalized_role = role.strip()

        if normalized_role not in GROUP_MEMBER_ROLES:
            raise ChurchGroupValidationError(
                "Group member role is invalid"
            )

        group_membership.role = normalized_role

    if member_status is not None:
        normalized_status = member_status.strip()

        if normalized_status not in GROUP_MEMBER_STATUSES:
            raise ChurchGroupValidationError(
                "Group member status is invalid"
            )

        group_membership.status = normalized_status

    db.flush()

    return group_membership


def leave_church_group_member(
    db: Session,
    *,
    user: User,
    church_id: int,
    group_id: int,
    group_membership_id: int,
) -> ChurchGroupMembership:
    """Preserve membership history while removing active group access."""

    _require_group_management(
        db,
        user=user,
        church_id=church_id,
    )

    group_membership = get_church_group_membership(
        db,
        church_id=church_id,
        group_id=group_id,
        group_membership_id=group_membership_id,
    )

    if group_membership.status == GROUP_MEMBER_STATUS_LEFT:
        raise ChurchGroupValidationError(
            "Church member has already left this group"
        )

    group_membership.status = GROUP_MEMBER_STATUS_LEFT
    db.flush()

    return group_membership
