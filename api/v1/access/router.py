"""
XynaFaith V2 application-facing effective access API.

This route exposes the stable effective-access contract used by
the V2 frontend. Commercial composition remains authoritative in
api.services.entitlement_service via effective_access_service.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.models.user import User
from api.schemas.access import (
    EffectiveAccessResponse,
    UsageVisibilityResponse,
)
from api.services.church_membership_service import (
    ChurchMembershipInactive,
    ChurchMembershipNotFound,
    get_active_church_membership,
)
from api.services.effective_access_service import get_effective_access
from api.services.usage_visibility_service import (
    UsageVisibilityConfigurationError,
    UsageVisibilityDenied,
    get_usage_visibility,
)


router = APIRouter(
    prefix="/access",
    tags=["Effective Access V2"],
)


def _validate_church_context(
    db: Session,
    *,
    church_id: int,
    user_id: int,
) -> None:
    """
    Require the requested Church context to belong to an active membership.

    Missing membership deliberately returns the same 404 used by Church Space
    authorization so callers cannot probe foreign Church Spaces.

    Inactive membership remains distinguishable from missing membership,
    matching the established Church Space authorization contract.
    """
    try:
        get_active_church_membership(
            db,
            church_id=church_id,
            user_id=user_id,
        )
    except ChurchMembershipNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Church Space not found",
        ) from exc
    except ChurchMembershipInactive as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Church membership is not active",
        ) from exc


@router.get(
    "/me",
    response_model=EffectiveAccessResponse,
)
def read_my_effective_access(
    church_id: Optional[int] = Query(
        default=None,
        ge=1,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EffectiveAccessResponse:
    """
    Return effective product access for the authenticated user.

    Without church_id, only personal/baseline access is resolved.

    With church_id, the Church context must first be proven by active
    membership before Church-paid capabilities may participate in the
    effective-access result.
    """
    if church_id is not None:
        _validate_church_context(
            db,
            church_id=church_id,
            user_id=current_user.id,
        )

    return get_effective_access(
        db,
        current_user,
        church_id=church_id,
    )


@router.get(
    "/usage",
    response_model=UsageVisibilityResponse,
)
def read_my_usage_visibility(
    church_id: Optional[int] = Query(
        default=None,
        ge=1,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UsageVisibilityResponse:
    """
    Return the authenticated user's current Xyniva Chat quota state.

    Church context is optional. When supplied, active Church membership
    is validated before effective entitlement and quota ownership are
    resolved.
    """

    if church_id is not None:
        _validate_church_context(
            db,
            church_id=church_id,
            user_id=current_user.id,
        )

    try:
        usage = get_usage_visibility(
            db,
            user=current_user,
            entitlement_key="xyniva.chat",
            metric="conversation_turn",
            church_id=church_id,
        )
    except UsageVisibilityDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Xyniva Chat is not available",
        ) from exc
    except UsageVisibilityConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Xyniva Chat usage is not available for this access configuration",
        ) from exc

    return UsageVisibilityResponse(
        entitlement_key=usage.entitlement_key,
        metric=usage.metric,
        quota_scope=usage.quota_owner_type,
        allowance_units=usage.allowance_units,
        consumed_units=usage.consumed_units,
        reserved_units=usage.reserved_units,
        available_units=usage.available_units,
        period_start=usage.period_start,
        period_end=usage.period_end,
    )
