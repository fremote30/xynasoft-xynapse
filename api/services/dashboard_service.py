from sqlalchemy.orm import Session
from sqlalchemy import func
from api.models.sermon import Sermon
from api.models.shared_sermon import SharedSermon


# =========================
# 📊 SUMMARY METRICS
# =========================
def get_dashboard_summary(db: Session, user_id: int):

    # Total sermons created by pastor
    total_sermons = db.query(Sermon).filter(
        Sermon.author_id == user_id
    ).count()

    # Total views (members reached)
    total_views = db.query(func.coalesce(func.sum(Sermon.views), 0)).filter(
        Sermon.author_id == user_id
    ).scalar()

    # Total shares (real tracking)
    total_shares = db.query(func.count(SharedSermon.id)).join(
        Sermon, Sermon.id == SharedSermon.sermon_id
    ).filter(
        Sermon.author_id == user_id
    ).scalar()

    # Engagement = shares / views
    engagement = 0
    if total_views and total_views > 0:
        engagement = round((total_shares / total_views) * 100, 2)

    return {
        "total_sermons": total_sermons,
        "members_reached": total_views,
        "total_shares": total_shares,
        "engagement": engagement
    }


# =========================
# 📈 MAIN DASHBOARD DATA
# =========================
def get_dashboard_data(db: Session, user_id: int):

    # Top sermon (most viewed)
    top_sermon = db.query(Sermon).filter(
        Sermon.author_id == user_id
    ).order_by(Sermon.views.desc()).first()

    # All sermons for chart
    sermons = db.query(Sermon).filter(
        Sermon.author_id == user_id
    ).all()

    # Total views
    total_views = sum(s.views for s in sermons)

    # Chart data (group by date)
    chart_map = {}

    for s in sermons:
        date = s.created_at.strftime("%Y-%m-%d")
        chart_map[date] = chart_map.get(date, 0) + 1

    chart_data = [
        {"date": k, "count": v}
        for k, v in sorted(chart_map.items())
    ]

    return {
        "top_sermon": top_sermon.title if top_sermon else None,
        "total_views": total_views,
        "chart_data": chart_data
    }


# =========================
# 📝 RECENT SERMONS
# =========================
def get_recent_sermons(db: Session, user_id: int):

    sermons = db.query(Sermon).filter(
        Sermon.author_id == user_id
    ).order_by(Sermon.created_at.desc()).limit(5).all()

    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at,
            "shares": s.shares,
            "views": s.views
        }
        for s in sermons
    ]