from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from datetime import datetime, timedelta

from api.db.database import get_db
from api.core.dependencies import get_current_user

from api.services.prayer_service import (
    display_name,
    is_admin,
    is_pastor_or_admin,
    create_notification,
    prayer_to_dict
)

from api.models.prayer import (
    Prayer,
    PrayerRecipient,
    PrayerReaction,
    PrayerComment,
    PrayerBookmark,
    PrayerReport,
    PrayerNotification
)
from api.schemas.prayer import (
    PrayerCreate,
    PrayerUpdateStatus,
    PrayerReactionCreate,
    PrayerCommentCreate,
    PrayerReportCreate
)

router = APIRouter()


# =====================================
# CREATE PRAYER
# =====================================
@router.post("/prayers")
def create_prayer(
    payload: PrayerCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    message = payload.message.strip()

    if not message:
        raise HTTPException(status_code=400, detail="Prayer message required")

    visibility = payload.visibility or "community"

    has_recipients = bool(payload.recipients)

    if has_recipients and visibility == "community":
        visibility = "mixed"

    if not has_recipients and visibility not in ["community"]:
        raise HTTPException(
            status_code=400,
            detail="Selected recipients are required for private prayers"
        )

    prayer = Prayer(
        message=message,
        category=payload.category,
        visibility=visibility,
        is_anonymous=payload.is_anonymous,
        user_id=user.id,
        user_name=user.name or user.email or "XynaFaith User"
    )

    db.add(prayer)
    db.flush()

    for recipient in payload.recipients:
        if recipient.user_id == user.id:
            continue

        prayer_recipient = PrayerRecipient(
            prayer_id=prayer.id,
            recipient_user_id=recipient.user_id,
            recipient_role=recipient.role
        )

        db.add(prayer_recipient)

        create_notification(
            db,
            recipient.user_id,
            prayer.id,
            "prayer_received",
            f"{user.name} sent you a prayer request."
        )

    db.commit()
    db.refresh(prayer)

    return {
        "success": True,
        "prayer": prayer_to_dict(prayer, user, db)
    }

# =====================================
# PRAYER INBOX
# =====================================
@router.get("/prayers/inbox")
def prayer_inbox(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    rows = db.query(PrayerRecipient).filter(
        PrayerRecipient.recipient_user_id == user.id
    ).order_by(
        PrayerRecipient.created_at.desc()
    ).all()

    prayers = []

    for row in rows:
        prayer = db.query(Prayer).filter(
            Prayer.id == row.prayer_id,
            Prayer.is_hidden == False
        ).first()

        if prayer:
            item = prayer_to_dict(prayer, user, db)
            item["recipient_status"] = {
                "is_read": row.is_read,
                "prayed_at": row.prayed_at,
                "responded_at": row.responded_at
            }
            prayers.append(item)

    return {
        "success": True,
        "items": prayers
    }


# =====================================
# SENT PRAYERS
# =====================================
@router.get("/prayers/sent")
def sent_prayers(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    prayers = db.query(Prayer).filter(
        Prayer.user_id == user.id,
        Prayer.is_hidden == False
    ).order_by(
        Prayer.created_at.desc()
    ).all()

    return {
        "success": True,
        "items": [
            prayer_to_dict(p, user, db)
            for p in prayers
        ]
    }
# =====================================
# PRAYER FEED
# =====================================
@router.get("/prayers/feed")
def prayer_feed(
    filter: str = Query("recent"),
    search: str = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    query = db.query(Prayer).filter(Prayer.is_hidden == False,Prayer.visibility.in_(["community", "mixed"]))
    if search:
        query = query.filter(
            or_(
                Prayer.message.ilike(f"%{search}%"),
                Prayer.category.ilike(f"%{search}%"),
                Prayer.user_name.ilike(f"%{search}%")
            )
        )

    if filter == "answered":
        query = query.filter(Prayer.status == "answered")
    elif filter == "my":
        query = query.filter(Prayer.user_id == user.id)
    elif filter == "most_prayed":
        query = query.order_by(Prayer.prayer_count.desc(), Prayer.created_at.desc())
    else:
        query = query.order_by(Prayer.created_at.desc())

    prayers = query.offset(skip).limit(limit).all()

    return {
        "success": True,
        "items": [prayer_to_dict(p, user, db) for p in prayers],
        "next_skip": skip + limit
    }


# =====================================
# REACT TO PRAYER
# =====================================
@router.post("/prayers/{prayer_id}/react")
def react_to_prayer(
    prayer_id: int,
    payload: PrayerReactionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if payload.reaction_type not in ["prayed", "support"]:
        raise HTTPException(status_code=400, detail="Invalid reaction type")

    prayer = db.query(Prayer).filter(
        Prayer.id == prayer_id,
        Prayer.is_hidden == False
    ).first()

    if not prayer:
        raise HTTPException(status_code=404, detail="Prayer not found")

    existing = db.query(PrayerReaction).filter(
        PrayerReaction.prayer_id == prayer_id,
        PrayerReaction.user_id == user.id,
        PrayerReaction.reaction_type == payload.reaction_type
    ).first()

    if existing:
        return {
            "success": True,
            "message": "Reaction already exists",
            "prayer": prayer_to_dict(prayer, user, db)
        }

    reaction = PrayerReaction(
        prayer_id=prayer_id,
        user_id=user.id,
        reaction_type=payload.reaction_type
    )

    db.add(reaction)

    if payload.reaction_type == "prayed":
        prayer.prayer_count = (prayer.prayer_count or 0) + 1
        notification_message = f"{user.name} prayed for your request."
        notification_type = "prayed"
    else:
        prayer.support_count = (prayer.support_count or 0) + 1
        notification_message = f"{user.name} supported your prayer request."
        notification_type = "support"

    if prayer.user_id != user.id:
        create_notification(
            db,
            prayer.user_id,
            prayer.id,
            notification_type,
            notification_message
        )

    db.commit()
    db.refresh(prayer)

    return {
        "success": True,
        "prayer": prayer_to_dict(prayer, user, db)
    }


# =====================================
# COMMENTS
# =====================================
@router.post("/prayers/{prayer_id}/comments")
def create_comment(
    prayer_id: int,
    payload: PrayerCommentCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    prayer = db.query(Prayer).filter(
        Prayer.id == prayer_id,
        Prayer.is_hidden == False
    ).first()

    if not prayer:
        raise HTTPException(status_code=404, detail="Prayer not found")

    if prayer.is_locked:
        raise HTTPException(status_code=403, detail="Comments are locked")

    comment_text = payload.comment.strip()

    if not comment_text:
        raise HTTPException(status_code=400, detail="Comment required")

    comment = PrayerComment(
        prayer_id=prayer.id,
        user_id=user.id,
        user_name=user.name or user.email or "XynaFaith User",
        parent_id=payload.parent_id,
        comment=comment_text,
        is_pastor_response=is_pastor_or_admin(user)
    )

    db.add(comment)

    prayer.comment_count = (prayer.comment_count or 0) + 1

    if prayer.user_id != user.id:
        create_notification(
            db,
            prayer.user_id,
            prayer.id,
            "comment",
            f"{user.name} commented on your prayer."
        )

    db.commit()
    db.refresh(comment)

    return {
        "success": True,
        "comment": {
            "id": comment.id,
            "prayer_id": comment.prayer_id,
            "user_name": comment.user_name,
            "comment": comment.comment,
            "parent_id": comment.parent_id,
            "is_pastor_response": comment.is_pastor_response,
            "is_pinned": comment.is_pinned,
            "created_at": comment.created_at
        }
    }


@router.get("/prayers/{prayer_id}/comments")
def get_comments(
    prayer_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    comments = db.query(PrayerComment).filter(
        PrayerComment.prayer_id == prayer_id,
        PrayerComment.is_hidden == False
    ).order_by(
        PrayerComment.is_pinned.desc(),
        PrayerComment.created_at.asc()
    ).all()

    return {
        "success": True,
        "items": [
            {
                "id": c.id,
                "prayer_id": c.prayer_id,
                "user_name": c.user_name,
                "comment": c.comment,
                "parent_id": c.parent_id,
                "is_pastor_response": c.is_pastor_response,
                "is_pinned": c.is_pinned,
                "created_at": c.created_at
            }
            for c in comments
        ]
    }


# =====================================
# BOOKMARK
# =====================================
@router.post("/prayers/{prayer_id}/bookmark")
def toggle_bookmark(
    prayer_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    prayer = db.query(Prayer).filter(
        Prayer.id == prayer_id,
        Prayer.is_hidden == False
    ).first()

    if not prayer:
        raise HTTPException(status_code=404, detail="Prayer not found")

    existing = db.query(PrayerBookmark).filter(
        PrayerBookmark.prayer_id == prayer_id,
        PrayerBookmark.user_id == user.id
    ).first()

    if existing:
        db.delete(existing)
        bookmarked = False
    else:
        db.add(PrayerBookmark(prayer_id=prayer_id, user_id=user.id))
        bookmarked = True

    db.commit()

    return {
        "success": True,
        "bookmarked": bookmarked
    }


# =====================================
# SHARE COUNT
# =====================================
@router.post("/prayers/{prayer_id}/share")
def share_prayer(
    prayer_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    prayer = db.query(Prayer).filter(
        Prayer.id == prayer_id,
        Prayer.is_hidden == False
    ).first()

    if not prayer:
        raise HTTPException(status_code=404, detail="Prayer not found")

    prayer.share_count = (prayer.share_count or 0) + 1
    db.commit()

    return {
        "success": True,
        "share_count": prayer.share_count
    }


# =====================================
# UPDATE PRAYER STATUS
# =====================================
@router.patch("/prayers/{prayer_id}/status")
def update_prayer_status(
    prayer_id: int,
    payload: PrayerUpdateStatus,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if payload.status not in ["still_praying", "partially_answered", "answered"]:
        raise HTTPException(status_code=400, detail="Invalid prayer status")

    prayer = db.query(Prayer).filter(Prayer.id == prayer_id).first()

    if not prayer:
        raise HTTPException(status_code=404, detail="Prayer not found")

    if prayer.user_id != user.id and not is_admin(user):
        raise HTTPException(status_code=403, detail="Not allowed")

    prayer.status = payload.status
    prayer.answered_at = datetime.utcnow() if payload.status == "answered" else None

    db.commit()
    db.refresh(prayer)

    return {
        "success": True,
        "prayer": prayer_to_dict(prayer, user, db)
    }


# =====================================
# REPORT PRAYER
# =====================================
@router.post("/prayers/{prayer_id}/report")
def report_prayer(
    prayer_id: int,
    payload: PrayerReportCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    prayer = db.query(Prayer).filter(Prayer.id == prayer_id).first()

    if not prayer:
        raise HTTPException(status_code=404, detail="Prayer not found")

    report = PrayerReport(
        prayer_id=prayer_id,
        user_id=user.id,
        reason=payload.reason,
        details=payload.details
    )

    db.add(report)
    db.commit()

    return {
        "success": True,
        "message": "Prayer reported"
    }


# =====================================
# ADMIN MODERATION
# =====================================
@router.patch("/admin/prayers/{prayer_id}/hide")
def hide_prayer(
    prayer_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")

    prayer = db.query(Prayer).filter(Prayer.id == prayer_id).first()

    if not prayer:
        raise HTTPException(status_code=404, detail="Prayer not found")

    prayer.is_hidden = True
    db.commit()

    return {"success": True}


@router.patch("/admin/prayers/{prayer_id}/lock")
def lock_prayer_comments(
    prayer_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")

    prayer = db.query(Prayer).filter(Prayer.id == prayer_id).first()

    if not prayer:
        raise HTTPException(status_code=404, detail="Prayer not found")

    prayer.is_locked = True
    db.commit()

    return {"success": True}


@router.delete("/admin/prayers/{prayer_id}")
def delete_prayer(
    prayer_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if not is_admin(user):
        raise HTTPException(status_code=403, detail="Admin only")

    prayer = db.query(Prayer).filter(Prayer.id == prayer_id).first()

    if not prayer:
        raise HTTPException(status_code=404, detail="Prayer not found")

    db.delete(prayer)
    db.commit()

    return {"success": True}


# =====================================
# ANALYTICS
# =====================================
@router.get("/prayers/analytics")
def prayer_analytics(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    week_start = datetime.utcnow() - timedelta(days=7)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_prayers = db.query(Prayer).filter(Prayer.is_hidden == False).count()

    prayers_this_week = db.query(Prayer).filter(
        Prayer.is_hidden == False,
        Prayer.created_at >= week_start
    ).count()

    answered_prayers = db.query(Prayer).filter(
        Prayer.is_hidden == False,
        Prayer.status == "answered"
    ).count()

    people_praying_today = db.query(func.count(func.distinct(PrayerReaction.user_id))).filter(
        PrayerReaction.created_at >= today_start,
        PrayerReaction.reaction_type == "prayed"
    ).scalar() or 0

    top_categories = db.query(
        Prayer.category,
        func.count(Prayer.id)
    ).filter(
        Prayer.is_hidden == False,
        Prayer.category.isnot(None)
    ).group_by(
        Prayer.category
    ).order_by(
        func.count(Prayer.id).desc()
    ).limit(5).all()

    return {
        "success": True,
        "total_prayers": total_prayers,
        "prayers_this_week": prayers_this_week,
        "answered_prayers": answered_prayers,
        "people_praying_today": people_praying_today,
        "top_categories": [
            {
                "category": category,
                "count": count
            }
            for category, count in top_categories
        ]
    }


# =====================================
# EXISTING DASHBOARD ENDPOINTS
# =====================================
@router.get("/dashboard/recent-prayers")
def recent_prayers(
    db: Session = Depends(get_db)
):
    prayers = db.query(Prayer).filter(
        Prayer.is_hidden == False
    ).order_by(
        Prayer.created_at.desc()
    ).limit(10).all()

    return [
        {
            "id": p.id,
            "message": p.message,
            "user_name": display_name(p),
            "status": p.status,
            "prayer_count": p.prayer_count or 0,
            "support_count": p.support_count or 0,
            "comment_count": p.comment_count or 0,
            "created_at": p.created_at
        }
        for p in prayers
    ]


@router.get("/dashboard/member-prayers")
def member_prayers(
    db: Session = Depends(get_db)
):
    prayers = db.query(Prayer).filter(
        Prayer.is_hidden == False
    ).order_by(
        Prayer.created_at.desc()
    ).limit(10).all()

    return [
        {
            "id": p.id,
            "message": p.message,
            "user_name": display_name(p),
            "status": p.status,
            "prayer_count": p.prayer_count or 0,
            "support_count": p.support_count or 0,
            "comment_count": p.comment_count or 0,
            "created_at": p.created_at
        }
        for p in prayers
    ]

# =====================================
# NOTIFICATIONS
# =====================================
@router.get("/prayers/notifications")
def get_prayer_notifications(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    notifications = db.query(PrayerNotification).filter(
        PrayerNotification.user_id == user.id
    ).order_by(
        PrayerNotification.created_at.desc()
    ).limit(20).all()

    unread_count = db.query(PrayerNotification).filter(
        PrayerNotification.user_id == user.id,
        PrayerNotification.is_read == False
    ).count()

    return {
        "success": True,
        "unread_count": unread_count,
        "items": [
            {
                "id": n.id,
                "prayer_id": n.prayer_id,
                "notification_type": n.notification_type,
                "message": n.message,
                "is_read": n.is_read,
                "created_at": n.created_at
            }
            for n in notifications
        ]
    }


@router.patch("/prayers/notifications/read")
def mark_prayer_notifications_read(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    notifications = db.query(PrayerNotification).filter(
        PrayerNotification.user_id == user.id,
        PrayerNotification.is_read == False
    ).all()

    for notification in notifications:
        notification.is_read = True

    db.commit()

    return {
        "success": True
    }