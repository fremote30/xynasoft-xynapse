from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

# =========================
# DB
# =========================
from api.db.database import get_db

# =========================
# MODELS
# =========================
from api.models.sermon import Sermon
from api.models.shared_sermon import SharedSermon
from api.models.user import User
from api.models.pastor_member import PastorMember
from api.models.prayer import Prayer  # 🔥 NEW Prayer Wall model
from api.models.follow import PastorFollower

# =========================
# AUTH
# =========================
from api.core.dependencies import get_current_user

# =========================
# AI
# =========================
from api.services.ai_insights import generate_dashboard_insights

from api.services.platform_service import PlatformService

router = APIRouter()

# ================================
# MAIN DASHBOARD
# ================================
@router.get("/dashboard")
def get_dashboard(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    total_sermons = db.query(func.count(Sermon.id)).filter(Sermon.author_id == user.id).scalar() or 0
    total_views = db.query(func.coalesce(func.sum(Sermon.views), 0)).filter(Sermon.author_id == user.id).scalar() or 0
    total_shares = db.query(func.count(SharedSermon.id)).join(Sermon, Sermon.id == SharedSermon.sermon_id)\
        .filter(Sermon.author_id == user.id).scalar() or 0

    top_sermon_query = db.query(Sermon.title, func.count(SharedSermon.id).label("share_count"))\
        .outerjoin(SharedSermon, SharedSermon.sermon_id == Sermon.id)\
        .filter(Sermon.author_id == user.id)\
        .group_by(Sermon.id)\
        .order_by(func.count(SharedSermon.id).desc()).first()

    top_sermon = top_sermon_query.title if top_sermon_query else "N/A"

    recent_sermons = db.query(Sermon).filter(Sermon.author_id == user.id)\
        .order_by(Sermon.created_at.desc()).limit(5).all()

    recent_data = [
        {"id": s.id, "title": s.title, "created_at": s.created_at, "shares": len(s.shared_sermons) if s.shared_sermons else 0}
        for s in recent_sermons
    ]

    return {
        "user": {"id": user.id, "name": getattr(user, "name", "User")},
        "stats": {"sermons": total_sermons, "drafts": 0, "collaborations": total_shares},
        "recent": recent_data,
        "total_sermons": total_sermons,
        "total_views": total_views,
        "total_shares": total_shares,
        "top_sermon": top_sermon,
    }

# ================================
# DASHBOARD SUMMARY
# ================================
@router.get("/dashboard/summary")
def get_dashboard_summary(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    total_sermons = db.query(func.count(Sermon.id)).filter(Sermon.author_id == user.id).scalar() or 0
    total_views = db.query(func.coalesce(func.sum(Sermon.views), 0)).filter(Sermon.author_id == user.id).scalar() or 0
    total_shares = db.query(func.count(SharedSermon.id)).join(Sermon, Sermon.id == SharedSermon.sermon_id)\
        .filter(Sermon.author_id == user.id).scalar() or 0
    total_members = db.query(func.count(PastorMember.member_id)).scalar() or 0
    engagement = round((total_shares / total_views) * 100, 2) if total_views > 0 else 0
    platform_stats = PlatformService.get_platform_stats(db)

    return {
        "total_sermons": total_sermons,
        "total_members": total_members,
        "total_shares": total_shares,
        "engagement": engagement,
        # Platform-wide community statistics
        "platform": platform_stats
    }

# ================================
# MEMBER DASHBOARD SUMMARY
# ================================
@router.get("/dashboard/member-summary")
def get_member_dashboard_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    if user.role != "member":
        return {
            "following_pastors": 0,
            "saved_sermons": 0,
            "prayer_requests": 0,
            "answered_prayers": 0
        }

    following_pastors = db.query(
        func.count(PastorFollower.id)
    ).filter(
        PastorFollower.member_id == user.id
    ).scalar() or 0

    prayer_requests = db.query(
        func.count(Prayer.id)
    ).filter(
        Prayer.user_id == user.id,
        Prayer.is_hidden == False
    ).scalar() or 0

    answered_prayers = db.query(
        func.count(Prayer.id)
    ).filter(
        Prayer.user_id == user.id,
        Prayer.is_hidden == False,
        Prayer.status == "answered"
    ).scalar() or 0

    # Saved-sermon bookmarking has not been implemented yet.
    saved_sermons = 0

    return {
        "following_pastors": following_pastors,
        "saved_sermons": saved_sermons,
        "prayer_requests": prayer_requests,
        "answered_prayers": answered_prayers
    }

# ================================
# RECENT SERMONS
# ================================
@router.get("/dashboard/recent-sermons")
def get_recent_sermons(db: Session = Depends(get_db), user=Depends(get_current_user)):
    sermons = db.query(Sermon).filter(Sermon.author_id == user.id).order_by(Sermon.created_at.desc()).limit(5).all()
    return [
        {"id": s.id, "title": s.title, "created_at": s.created_at, "shares": len(s.shared_sermons) if s.shared_sermons else 0}
        for s in sermons
    ]

# ================================
# TOP SERMONS
# ================================
@router.get("/dashboard/top-sermons")
def get_top_sermons(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    query = (
        db.query(
            Sermon.id,
            Sermon.title,
            Sermon.scripture,
            Sermon.author_id,
            User.name.label("author_name"),
            Sermon.views,
            func.count(
                SharedSermon.id
            ).label("shares")
        )
        .join(
            User,
            User.id == Sermon.author_id
        )
        .outerjoin(
            SharedSermon,
            SharedSermon.sermon_id == Sermon.id
        )
    )

    # =====================================
    # MEMBER EXPERIENCE
    # Members discover public sermons from
    # pastors across the platform.
    # =====================================
    if user.role == "member":
        query = query.filter(
            Sermon.is_public == 1,
            User.role.in_([
                "pastor",
                "admin"
            ])
        )

    # =====================================
    # PASTOR / ADMIN DASHBOARD
    # Keep the existing behavior by showing
    # sermons authored by the current user.
    # =====================================
    else:
        query = query.filter(
            Sermon.author_id == user.id
        )

    top_sermons = (
        query
        .group_by(
            Sermon.id,
            Sermon.title,
            Sermon.scripture,
            Sermon.author_id,
            User.name,
            Sermon.views
        )
        .order_by(
            func.count(
                SharedSermon.id
            ).desc(),
            Sermon.views.desc(),
            Sermon.created_at.desc()
        )
        .limit(5)
        .all()
    )

    return [
        {
            "id": sermon.id,
            "title": sermon.title,
            "scripture": sermon.scripture or "",
            "author_id": sermon.author_id,
            "author_name": sermon.author_name or "Pastor",
            "views": sermon.views or 0,
            "shares": sermon.shares or 0
        }
        for sermon in top_sermons
    ]

# ================================
# AI INSIGHTS
# ================================
@router.get("/dashboard/insights")
def get_dashboard_insights(db: Session = Depends(get_db), user=Depends(get_current_user)):
    total_sermons = db.query(func.count(Sermon.id)).filter(Sermon.author_id == user.id).scalar() or 0
    total_shares = db.query(func.count(SharedSermon.id)).join(Sermon, SharedSermon.sermon_id == Sermon.id)\
        .filter(Sermon.author_id == user.id).scalar() or 0
    top_sermons = db.query(Sermon.title, func.count(SharedSermon.id).label("shares"))\
        .outerjoin(SharedSermon, SharedSermon.sermon_id == Sermon.id)\
        .filter(Sermon.author_id == user.id)\
        .group_by(Sermon.id)\
        .order_by(func.count(SharedSermon.id).desc())\
        .limit(5).all()

    ai_input = {
        "total_sermons": total_sermons,
        "total_shares": total_shares,
        "top_sermons": [{"title": s.title, "shares": s.shares} for s in top_sermons]
    }

    insights = generate_dashboard_insights(ai_input)

    return {"insights": insights}

# ================================
# MEMBER DASHBOARD PRAYER WALL
# ================================
@router.get("/dashboard/prayer-wall")
def get_prayer_wall(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    prayers = (
        db.query(Prayer)
        .filter(
            Prayer.user_id == user.id,
            Prayer.is_hidden == False
        )
        .order_by(
            Prayer.created_at.desc()
        )
        .limit(10)
        .all()
    )

    return [
        {
            "id": prayer.id,
            "message": prayer.message,
            "category": prayer.category,
            "status": prayer.status,
            "visibility": prayer.visibility,
            "prayer_count": prayer.prayer_count or 0,
            "support_count": prayer.support_count or 0,
            "comment_count": prayer.comment_count or 0,
            "answered_at": prayer.answered_at,
            "answer_testimony": prayer.answer_testimony,
            "created_at": prayer.created_at
        }
        for prayer in prayers
    ]