# =====================================
# XynaFAITH PLATFORM SERVICE
# Single source of truth for
# platform-wide community information.
# =====================================

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.models.user import User
from api.models.pastor_profile import PastorProfile
from api.models.sermon import Sermon
from api.models.prayer import Prayer
from api.models.follow import PastorFollower


class PlatformService:

    # =====================================
    # PLATFORM-WIDE COUNTS
    # =====================================
    @staticmethod
    def get_platform_stats(
        db: Session
    ) -> dict:

        pastor_count = (
            db.query(func.count(User.id))
            .filter(
                User.role.in_(
                    ["pastor", "admin"]
                )
            )
            .scalar()
            or 0
        )

        member_count = (
            db.query(func.count(User.id))
            .filter(
                User.role == "member"
            )
            .scalar()
            or 0
        )

        sermon_count = (
            db.query(func.count(Sermon.id))
            .scalar()
            or 0
        )

        prayer_count = (
            db.query(func.count(Prayer.id))
            .filter(
                Prayer.is_hidden.is_(False)
            )
            .scalar()
            or 0
        )

        # Count distinct non-empty church names.
        church_count = (
            db.query(
                func.count(
                    func.distinct(
                        func.lower(
                            func.trim(
                                PastorProfile.church_name
                            )
                        )
                    )
                )
            )
            .filter(
                PastorProfile.church_name.isnot(
                    None
                ),
                func.trim(
                    PastorProfile.church_name
                ) != ""
            )
            .scalar()
            or 0
        )

        follower_count = (
            db.query(
                func.count(
                    PastorFollower.id
                )
            )
            .scalar()
            or 0
        )

        return {
            "pastors": int(pastor_count),
            "members": int(member_count),
            "churches": int(church_count),
            "sermons": int(sermon_count),
            "prayers": int(prayer_count),
            "connections": int(follower_count)
        }

    # =====================================
    # FEATURED PASTOR
    # =====================================
    @staticmethod
    def get_featured_pastor(
        db: Session,
        current_user: Optional[User] = None
    ) -> Optional[dict]:

        follower_counts = (
            db.query(
                PastorFollower.pastor_id.label(
                    "pastor_id"
                ),
                func.count(
                    PastorFollower.id
                ).label(
                    "follower_count"
                )
            )
            .group_by(
                PastorFollower.pastor_id
            )
            .subquery()
        )

        sermon_counts = (
            db.query(
                Sermon.author_id.label(
                    "pastor_id"
                ),
                func.count(
                    Sermon.id
                ).label(
                    "sermon_count"
                )
            )
            .group_by(
                Sermon.author_id
            )
            .subquery()
        )

        row = (
            db.query(
                User,
                PastorProfile,
                func.coalesce(
                    follower_counts.c.follower_count,
                    0
                ).label(
                    "followers"
                ),
                func.coalesce(
                    sermon_counts.c.sermon_count,
                    0
                ).label(
                    "sermon_count"
                )
            )
            .join(
                PastorProfile,
                PastorProfile.user_id == User.id
            )
            .outerjoin(
                follower_counts,
                follower_counts.c.pastor_id
                == User.id
            )
            .outerjoin(
                sermon_counts,
                sermon_counts.c.pastor_id
                == User.id
            )
            .filter(
                User.role.in_(
                    ["pastor", "admin"]
                ),
                PastorProfile.visibility.in_(
                    ["public", "members"]
                )
            )
            .order_by(
                func.coalesce(
                    follower_counts.c.follower_count,
                    0
                ).desc(),
                func.coalesce(
                    sermon_counts.c.sermon_count,
                    0
                ).desc(),
                User.name.asc()
            )
            .first()
        )

        if not row:
            return None

        pastor = row[0]
        profile = row[1]
        followers = int(row[2] or 0)
        sermon_count = int(row[3] or 0)

        is_following = False

        if (
            current_user
            and current_user.role == "member"
        ):
            is_following = (
                db.query(PastorFollower.id)
                .filter(
                    PastorFollower.member_id
                    == current_user.id,
                    PastorFollower.pastor_id
                    == pastor.id
                )
                .first()
                is not None
            )

        location_parts = [
            profile.city,
            profile.state,
            profile.country
        ]

        location = (
            profile.location
            or ", ".join(
                part
                for part in location_parts
                if part
            )
            or "Global Ministry"
        )

        return {
            "id": pastor.id,
            "user_id": pastor.id,
            "name": pastor.name,
            "followers": followers,
            "sermon_count": sermon_count,
            "is_following": is_following,

            "church_name": (
                profile.church_name or ""
            ),
            "bio": profile.bio or "",
            "mission_statement": (
                profile.mission_statement or ""
            ),

            "denomination": (
                profile.denomination or ""
            ),
            "ministry_focus": (
                profile.ministry_focus or ""
            ),
            "specialties": (
                profile.specialties or ""
            ),

            "location": location,
            "city": profile.city or "",
            "state": profile.state or "",
            "country": profile.country or "",

            "profile_image": (
                profile.profile_image or ""
            ),
            "cover_image": (
                profile.cover_image or ""
            ),
            "church_logo": (
                profile.church_logo or ""
            ),

            "slug": profile.slug or "",
            "is_verified": bool(
                profile.is_verified
            ),
            "visibility": (
                profile.visibility or "public"
            )
        }

    # =====================================
    # RECENT COMMUNITY PRAYERS
    # =====================================
    @staticmethod
    def get_recent_prayers(
        db: Session,
        limit: int = 5
    ) -> list[dict]:

        prayers = (
            db.query(Prayer)
            .filter(
                Prayer.is_hidden.is_(False),
                Prayer.visibility.in_(
                    ["community", "mixed"]
                )
            )
            .order_by(
                Prayer.created_at.desc()
            )
            .limit(limit)
            .all()
        )

        return [
            {
                "id": prayer.id,

                "user_id": prayer.user_id,

                "user_name": (
                    "Anonymous"
                    if prayer.is_anonymous
                    else (
                        prayer.user_name
                        or "XynaFaith User"
                    )
                ),

                "message": prayer.message or "",

                "category": (
                    prayer.category or "Prayer"
                ),

                "status": (
                    prayer.status
                    or "still_praying"
                ),

                "prayer_count": int(
                    prayer.prayer_count or 0
                ),

                "support_count": int(
                    prayer.support_count or 0
                ),

                "comment_count": int(
                    prayer.comment_count or 0
                ),

                "share_count": int(
                    prayer.share_count or 0
                ),

                "created_at": prayer.created_at
            }
            for prayer in prayers
        ]

    # =====================================
    # TRENDING / RECENT SERMONS
    # =====================================
    @staticmethod
    def get_trending_sermons(
        db: Session,
        limit: int = 5
    ) -> list[dict]:

        rows = (
            db.query(
                Sermon,
                User.name.label(
                    "author_name"
                )
            )
            .join(
                User,
                User.id == Sermon.author_id
            )
            .filter(
                User.role.in_(
                    ["pastor", "admin"]
                )
            )
            .order_by(
                Sermon.created_at.desc()
            )
            .limit(limit)
            .all()
        )

        results = []

        for sermon, author_name in rows:

            content = sermon.content or ""

            if not isinstance(
                content,
                str
            ):
                content = str(content)

            results.append({
                "id": sermon.id,
                "title": (
                    sermon.title
                    or "Untitled Sermon"
                ),
                "author_id": sermon.author_id,
                "author_name": (
                    author_name
                    or "XynaFaith Pastor"
                ),
                "content_preview": (
                    content[:220]
                ),
                "created_at": sermon.created_at
            })

        return results

    # =====================================
    # RECENT COMMUNITY ACTIVITY
    # =====================================
    @staticmethod
    def get_recent_activity(
        db: Session,
        limit: int = 8
    ) -> list[dict]:

        activity = []

        recent_sermons = (
            db.query(
                Sermon,
                User.name.label(
                    "author_name"
                )
            )
            .join(
                User,
                User.id == Sermon.author_id
            )
            .order_by(
                Sermon.created_at.desc()
            )
            .limit(limit)
            .all()
        )

        for sermon, author_name in recent_sermons:
            activity.append({
                "type": "sermon",
                "icon": "✝",
                "title": (
                    sermon.title
                    or "New sermon"
                ),
                "description": (
                    f"{author_name or 'A pastor'} "
                    "published a sermon."
                ),
                "entity_id": sermon.id,
                "created_at": sermon.created_at
            })

        recent_prayers = (
            db.query(Prayer)
            .filter(
                Prayer.is_hidden.is_(False),
                Prayer.visibility.in_(
                    ["community", "mixed"]
                )
            )
            .order_by(
                Prayer.created_at.desc()
            )
            .limit(limit)
            .all()
        )

        for prayer in recent_prayers:
            name = (
                "Anonymous"
                if prayer.is_anonymous
                else (
                    prayer.user_name
                    or "A community member"
                )
            )

            activity.append({
                "type": "prayer",
                "icon": "🙏",
                "title": "New prayer request",
                "description": (
                    f"{name} shared a prayer request."
                ),
                "entity_id": prayer.id,
                "created_at": prayer.created_at
            })

        activity.sort(
            key=lambda item: (
                item["created_at"]
                is not None,
                item["created_at"]
            ),
            reverse=True
        )

        return activity[:limit]

    # =====================================
    # COMPLETE NETWORK OVERVIEW
    # =====================================
    @classmethod
    def get_network_overview(
        cls,
        db: Session,
        current_user: Optional[User] = None
    ) -> dict:

        return {
            "success": True,

            "platform": (
                cls.get_platform_stats(db)
            ),

            "featured_pastor": (
                cls.get_featured_pastor(
                    db,
                    current_user
                )
            ),

            "recent_prayers": (
                cls.get_recent_prayers(
                    db,
                    limit=5
                )
            ),

            "trending_sermons": (
                cls.get_trending_sermons(
                    db,
                    limit=5
                )
            ),

            "activity": (
                cls.get_recent_activity(
                    db,
                    limit=8
                )
            )
        }