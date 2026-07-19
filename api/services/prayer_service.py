from sqlalchemy.orm import Session

from api.models.prayer import (
    Prayer,
    PrayerReaction,
    PrayerBookmark,
    PrayerNotification,
    PrayerComment
)


def display_name(prayer: Prayer):
    return "Anonymous" if prayer.is_anonymous else prayer.user_name


def is_admin(user):
    return getattr(user, "role", "") == "admin"


def is_pastor_or_admin(user):
    return getattr(user, "role", "") in ["pastor", "admin"]


def create_notification(
    db: Session,
    user_id: int,
    prayer_id: int,
    notification_type: str,
    message: str
):
    notification = PrayerNotification(
        user_id=user_id,
        prayer_id=prayer_id,
        notification_type=notification_type,
        message=message
    )

    db.add(notification)


def prayer_to_dict(
    prayer: Prayer,
    user=None,
    db: Session = None
):
    has_prayed = False
    has_supported = False
    is_bookmarked = False
    can_update_status = False
    has_pastor_response = False
    featured_pastor_response = None

    if db:
        pastor_comment = (
            db.query(PrayerComment)
            .filter(
                PrayerComment.prayer_id == prayer.id,
                PrayerComment.is_hidden == False,
                PrayerComment.is_pastor_response == True
            )
            .order_by(
                PrayerComment.is_pinned.desc(),
                PrayerComment.created_at.asc()
            )
            .first()
        )

        if pastor_comment:
            has_pastor_response = True

            featured_pastor_response = {
                "id": pastor_comment.id,
                "user_name": pastor_comment.user_name,
                "comment": pastor_comment.comment,
                "is_pinned": pastor_comment.is_pinned,
                "created_at": pastor_comment.created_at
            }

    if user and db:
        has_prayed = (
            db.query(PrayerReaction)
            .filter(
                PrayerReaction.prayer_id == prayer.id,
                PrayerReaction.user_id == user.id,
                PrayerReaction.reaction_type == "prayed"
            )
            .first()
            is not None
        )

        has_supported = (
            db.query(PrayerReaction)
            .filter(
                PrayerReaction.prayer_id == prayer.id,
                PrayerReaction.user_id == user.id,
                PrayerReaction.reaction_type == "support"
            )
            .first()
            is not None
        )

        is_bookmarked = (
            db.query(PrayerBookmark)
            .filter(
                PrayerBookmark.prayer_id == prayer.id,
                PrayerBookmark.user_id == user.id
            )
            .first()
            is not None
        )

        can_update_status = (
            prayer.user_id == user.id or
            getattr(user, "role", "") == "admin"
        )

    return {
        "id": prayer.id,
        "message": prayer.message,
        "user_name": display_name(prayer),
        "category": prayer.category,
        "visibility": getattr(prayer, "visibility", "community"),
        "status": prayer.status,
        "is_anonymous": prayer.is_anonymous,
        "is_locked": prayer.is_locked,

        "prayer_count": prayer.prayer_count or 0,
        "support_count": prayer.support_count or 0,
        "comment_count": prayer.comment_count or 0,
        "share_count": prayer.share_count or 0,

        "created_at": prayer.created_at,
        "answered_at": prayer.answered_at,

        "answer_testimony": prayer.answer_testimony,
        "testimony_shared_at": prayer.testimony_shared_at,

        "has_pastor_response": has_pastor_response,
        "featured_pastor_response": featured_pastor_response,

        "has_prayed": has_prayed,
        "has_supported": has_supported,
        "is_bookmarked": is_bookmarked,
        "can_update_status": can_update_status
    }