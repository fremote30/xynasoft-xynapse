"""
XynaFaith V2 Church Space membership and authorization service.

V2 authorization must be based on the authenticated user's
ChurchMembership record rather than the user's legacy global role.
"""

from typing import Optional

from sqlalchemy.orm import Session

from api.core.church_rbac import (
    MEMBERSHIP_STATUS_ACTIVE,
    role_has_permission,
)
from api.models.church_membership import ChurchMembership


class ChurchMembershipNotFound(Exception):
    """User does not have a membership in the requested Church Space."""


class ChurchMembershipInactive(Exception):
    """User has a membership, but it is not active."""


class ChurchPermissionDenied(Exception):
    """Active membership does not grant the requested permission."""


def get_church_membership(
    db: Session,
    *,
    church_id: int,
    user_id: int,
) -> Optional[ChurchMembership]:
    """
    Return the membership for one user in one Church Space.

    No authorization decision is made here.
    """
    return (
        db.query(ChurchMembership)
        .filter(
            ChurchMembership.church_id == church_id,
            ChurchMembership.user_id == user_id,
        )
        .one_or_none()
    )


def get_active_church_membership(
    db: Session,
    *,
    church_id: int,
    user_id: int,
) -> ChurchMembership:
    """
    Require an active membership in the requested Church Space.

    Fails closed for missing, invited, suspended, or left memberships.
    """
    membership = get_church_membership(
        db,
        church_id=church_id,
        user_id=user_id,
    )

    if membership is None:
        raise ChurchMembershipNotFound()

    if membership.status != MEMBERSHIP_STATUS_ACTIVE:
        raise ChurchMembershipInactive()

    return membership


def require_church_permission(
    db: Session,
    *,
    church_id: int,
    user_id: int,
    permission: str,
) -> ChurchMembership:
    """
    Require an active membership with the requested church permission.

    Returns the trusted membership so callers may use its role/context.
    """
    membership = get_active_church_membership(
        db,
        church_id=church_id,
        user_id=user_id,
    )

    if not role_has_permission(
        membership.role,
        permission,
    ):
        raise ChurchPermissionDenied()

    return membership


def get_primary_church_membership(
    db: Session,
    *,
    user_id: int,
) -> Optional[ChurchMembership]:
    """
    Return the user's primary active Church Space membership, if any.
    """
    return (
        db.query(ChurchMembership)
        .filter(
            ChurchMembership.user_id == user_id,
            ChurchMembership.is_primary.is_(True),
            ChurchMembership.status == MEMBERSHIP_STATUS_ACTIVE,
        )
        .one_or_none()
    )
