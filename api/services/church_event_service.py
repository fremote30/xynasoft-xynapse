"""
Authoritative Church Space event mutations.

XynAssist may propose event content, but XynaFaith remains authoritative
for identity, Church Space context, authorization, commercial entitlement,
lifecycle state, validation, and persistence.
"""

from sqlalchemy.orm import Session

from api.core.church_rbac import PERMISSION_CONTENT_CREATE
from api.core.entitlements import ENTITLEMENT_EVENTS
from api.models.church_event import (
    EVENT_STATUS_DRAFT,
    ChurchEvent,
)
from api.models.user import User
from api.schemas.church_content import EventCreate
from api.services.church_membership_service import (
    ChurchMembershipInactive,
    ChurchMembershipNotFound,
    ChurchPermissionDenied,
    require_church_permission,
)
from api.services.effective_access_service import has_entitlement


class ChurchEventActionError(Exception):
    """Raised when a trusted event mutation is not permitted."""


def build_event_draft_for_user(
    *,
    db: Session,
    user: User,
    church_id: int,
    event_data: dict,
) -> ChurchEvent:
    """
    Build one authorized Church Space event draft.

    Lifecycle authority is deliberately not accepted from XynAssist.
    Every event created here is forced to draft.
    """

    if (
        not isinstance(church_id, int)
        or isinstance(church_id, bool)
        or church_id < 1
    ):
        raise ChurchEventActionError(
            "Trusted Church Space context is required"
        )

    try:
        require_church_permission(
            db,
            church_id=church_id,
            user_id=user.id,
            permission=PERMISSION_CONTENT_CREATE,
        )
    except ChurchMembershipNotFound as exc:
        raise ChurchEventActionError(
            "Church Space not found"
        ) from exc
    except ChurchMembershipInactive as exc:
        raise ChurchEventActionError(
            "Church membership is not active"
        ) from exc
    except ChurchPermissionDenied as exc:
        raise ChurchEventActionError(
            "Insufficient Church Space permission"
        ) from exc

    if not has_entitlement(
        db,
        user,
        ENTITLEMENT_EVENTS,
        church_id=church_id,
    ):
        raise ChurchEventActionError(
            "Church events are not available"
        )

    # Reuse the canonical product schema, while lifecycle remains trusted.
    try:
        validated = EventCreate.model_validate(
            {
                **event_data,
                "status": EVENT_STATUS_DRAFT,
            }
        )
    except Exception as exc:
        raise ChurchEventActionError(
            "Event details are invalid"
        ) from exc

    title = validated.title.strip()

    if not title:
        raise ChurchEventActionError(
            "Event title is required"
        )

    if (
        validated.ends_at is not None
        and validated.ends_at < validated.starts_at
    ):
        raise ChurchEventActionError(
            "Event end cannot precede start"
        )

    event = ChurchEvent(
        church_id=church_id,
        created_by_user_id=user.id,
        title=title,
        description=(
            validated.description.strip()
            if validated.description
            else None
        ),
        starts_at=validated.starts_at,
        ends_at=validated.ends_at,
        location=(
            validated.location.strip()
            if validated.location
            else None
        ),
        event_url=(
            str(validated.event_url)
            if validated.event_url
            else None
        ),
        status=EVENT_STATUS_DRAFT,
        published_at=None,
    )

    db.add(event)
    db.flush()

    return event
