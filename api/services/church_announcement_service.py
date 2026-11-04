"""
Authoritative Church Space announcement mutations.

XynAssist may propose announcement content, but XynaFaith remains
authoritative for identity, church membership, authorization,
commercial entitlement, lifecycle state, and persistence.
"""

from sqlalchemy.orm import Session

from api.core.church_rbac import PERMISSION_CONTENT_CREATE
from api.core.entitlements import ENTITLEMENT_ANNOUNCEMENTS
from api.models.church_announcement import (
    ANNOUNCEMENT_STATUS_DRAFT,
    ChurchAnnouncement,
)
from api.models.user import User
from api.services.church_membership_service import (
    ChurchMembershipInactive,
    ChurchMembershipNotFound,
    ChurchPermissionDenied,
    require_church_permission,
)
from api.services.effective_access_service import has_entitlement


class ChurchAnnouncementActionError(Exception):
    """Raised when a trusted announcement mutation is not permitted."""


def build_announcement_draft_for_user(
    *,
    db: Session,
    user: User,
    church_id: int,
    title: str,
    body: str,
) -> ChurchAnnouncement:
    """
    Build one authorized Church Space announcement draft.

    This function deliberately never accepts lifecycle status from
    XynAssist. Every announcement created here is a draft.
    """

    if (
        not isinstance(church_id, int)
        or isinstance(church_id, bool)
        or church_id < 1
    ):
        raise ChurchAnnouncementActionError(
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
        raise ChurchAnnouncementActionError(
            "Church Space not found"
        ) from exc
    except ChurchMembershipInactive as exc:
        raise ChurchAnnouncementActionError(
            "Church membership is not active"
        ) from exc
    except ChurchPermissionDenied as exc:
        raise ChurchAnnouncementActionError(
            "Insufficient Church Space permission"
        ) from exc

    if not has_entitlement(
        db,
        user,
        ENTITLEMENT_ANNOUNCEMENTS,
        church_id=church_id,
    ):
        raise ChurchAnnouncementActionError(
            "Church announcements are not available"
        )

    normalized_title = title.strip()
    normalized_body = body.strip()

    if not normalized_title or len(normalized_title) > 200:
        raise ChurchAnnouncementActionError(
            "Announcement title is invalid"
        )

    if not normalized_body:
        raise ChurchAnnouncementActionError(
            "Announcement body is invalid"
        )

    announcement = ChurchAnnouncement(
        church_id=church_id,
        author_user_id=user.id,
        title=normalized_title,
        body=normalized_body,
        status=ANNOUNCEMENT_STATUS_DRAFT,
        published_at=None,
    )

    db.add(announcement)
    db.flush()

    return announcement
