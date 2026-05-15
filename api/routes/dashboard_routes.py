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

# =========================
# AUTH
# =========================
from api.core.dependencies import get_current_user

# =========================
# AI
# =========================
from api.services.ai_insights import generate_dashboard_insights

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

    return {
        "total_sermons": total_sermons,
        "total_members": total_members,
        "total_shares": total_shares,
        "engagement": engagement
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
def get_top_sermons(db: Session = Depends(get_db), user=Depends(get_current_user)):
    top_sermons = db.query(Sermon.id, Sermon.title, func.count(SharedSermon.id).label("shares"))\
        .outerjoin(SharedSermon, SharedSermon.sermon_id == Sermon.id)\
        .filter(Sermon.author_id == user.id)\
        .group_by(Sermon.id)\
        .order_by(func.count(SharedSermon.id).desc())\
        .limit(5).all()

    return [{"id": s.id, "title": s.title, "shares": s.shares} for s in top_sermons]

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
# 🔥 PRAYER WALL (NEW)
# ================================
@router.get("/dashboard/prayer-wall")
def get_prayer_wall(db: Session = Depends(get_db), user=Depends(get_current_user)):
    prayers = db.query(Prayer).filter(Prayer.user_id == user.id).order_by(Prayer.created_at.desc()).limit(10).all()
    return [
        {"id": p.id, "title": p.title, "content": p.content, "created_at": p.created_at}
        for p in prayers
    ]