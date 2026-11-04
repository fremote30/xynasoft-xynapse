from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.core.dependencies import get_current_user
from api.db.database import get_db

from api.models.pastor_profile import PastorProfile
from api.models.prayer import Prayer
from api.models.sermon import Sermon
from api.models.user import User


router = APIRouter()


@router.get("/search")
def global_search(
    q: str = Query(
        ...,
        min_length=2,
        max_length=100,
    ),
    limit: int = Query(
        5,
        ge=1,
        le=20,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Global XynaFaith Search

    Searches:
    - Public sermons
    - Pastors
    - Churches (via PastorProfile)
    - Public prayer requests
    """

    search_term = q.strip()
    pattern = f"%{search_term}%"


    # =====================================
    # SERMONS
    # =====================================
    sermons = (
        db.query(
            Sermon,
            User.name.label("author_name"),
        )
        .join(
            User,
            User.id == Sermon.author_id,
        )
        .filter(
            Sermon.is_public == 1,
        )
        .filter(
            or_(
                Sermon.title.ilike(pattern),
                Sermon.scripture.ilike(pattern),
                Sermon.content.ilike(pattern),
            )
        )
        .order_by(
            Sermon.views.desc(),
            Sermon.created_at.desc(),
        )
        .limit(limit)
        .all()
    )


    sermon_results = [
        {
            "id": sermon.id,
            "title": sermon.title or "Untitled Sermon",
            "scripture": sermon.scripture or "",
            "author_id": sermon.author_id,
            "author_name": author_name or "Pastor",
            "views": sermon.views or 0,
            "created_at": sermon.created_at,
        }
        for sermon, author_name in sermons
    ]


    # =====================================
    # PASTORS
    # =====================================
    pastors = (
        db.query(
            User,
            PastorProfile,
        )
        .outerjoin(
            PastorProfile,
            PastorProfile.user_id == User.id,
        )
        .filter(
            User.role.in_(
                [
                    "pastor",
                    "admin",
                ]
            ),
        )
        .filter(
            or_(
                User.name.ilike(pattern),
                PastorProfile.church_name.ilike(pattern),
                PastorProfile.denomination.ilike(pattern),
                PastorProfile.city.ilike(pattern),
                PastorProfile.state.ilike(pattern),
                PastorProfile.country.ilike(pattern),
            )
        )
        .limit(limit)
        .all()
    )


    pastor_results = [
        {
            "id": user.id,
            "name": user.name or "Pastor",

            "church_name":
                profile.church_name
                if profile else "",

            "denomination":
                profile.denomination
                if profile else "",

            "city":
                profile.city
                if profile else "",

            "state":
                profile.state
                if profile else "",

            "country":
                profile.country
                if profile else "",

            "profile_image":
                getattr(
                    profile,
                    "profile_image",
                    "",
                )
                if profile else "",
        }

        for user, profile in pastors
    ]



    # =====================================
    # CHURCHES
    # Derived from PastorProfile
    # =====================================
    church_profiles = (
        db.query(PastorProfile)
        .filter(
            PastorProfile.church_name.isnot(None),
        )
        .filter(
            or_(
                PastorProfile.church_name.ilike(pattern),
                PastorProfile.city.ilike(pattern),
                PastorProfile.state.ilike(pattern),
                PastorProfile.country.ilike(pattern),
                PastorProfile.denomination.ilike(pattern),
            )
        )
        .limit(limit * 3)
        .all()
    )


    seen_churches = set()

    church_results = []


    for profile in church_profiles:

        church_name = (
            profile.church_name or ""
        ).strip()


        if not church_name:
            continue


        key = (
            church_name.lower(),
            (profile.city or "").lower(),
            (profile.state or "").lower(),
        )


        if key in seen_churches:
            continue


        seen_churches.add(key)


        church_results.append(
            {
                "id": profile.id,
                "pastor_user_id": profile.user_id,
                "name": church_name,
                "denomination":
                    profile.denomination or "",
                "city":
                    profile.city or "",
                "state":
                    profile.state or "",
                "country":
                    profile.country or "",
                "church_logo":
                    getattr(
                        profile,
                        "church_logo",
                        "",
                    )
                    or "",
            }
        )


        if len(church_results) >= limit:
            break



    # =====================================
    # PRAYERS
    # Matches Prayer Wall
    # =====================================
    prayers = (
        db.query(Prayer)
        .filter(
            Prayer.is_hidden == False,
        )
        .filter(
            Prayer.visibility.in_(
                [
                    "community",
                    "mixed",
                ]
            ),
        )
        .filter(
            or_(
                Prayer.message.ilike(pattern),
                Prayer.category.ilike(pattern),
                Prayer.user_name.ilike(pattern),
            )
        )
        .order_by(
            Prayer.created_at.desc(),
        )
        .limit(limit)
        .all()
    )


    prayer_results = [
        {
            "id": prayer.id,
            "message": prayer.message or "",
            "category": prayer.category or "",
            "status": prayer.status or "",
            "user_name":
                prayer.user_name or "Anonymous",
            "created_at":
                prayer.created_at,
        }

        for prayer in prayers
    ]



    # =====================================
    # FINAL RESPONSE
    # =====================================
    total_results = (
        len(sermon_results)
        +
        len(pastor_results)
        +
        len(church_results)
        +
        len(prayer_results)
    )


    return {
        "query": search_term,
        "sermons": sermon_results,
        "pastors": pastor_results,
        "churches": church_results,
        "prayers": prayer_results,
        "total_results": total_results,
    }