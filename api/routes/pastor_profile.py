from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from api.db.database import SessionLocal
from api.models.user import User
from api.models.pastor_profile import PastorProfile
from api.models.follow import PastorFollower
from api.models.sermon import Sermon
from api.core.security import decode_token


router = APIRouter(
    prefix="/pastor-profile",
    tags=["Pastor Profiles"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user_from_header(
    authorization: str,
    db: Session
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.split(" ")[1]
    payload = decode_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user_id = payload.get("sub")

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


def get_optional_user_from_header(
    authorization: str | None,
    db: Session
):
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ")[1]
    payload = decode_token(token)

    if not payload:
        return None

    user_id = payload.get("sub")

    return db.query(User).filter(
        User.id == int(user_id)
    ).first()

def profile_to_dict(profile: PastorProfile, user: User):
    return {
        "id": profile.id,
        "user_id": user.id,
        "name": user.name,
        "email": user.email,

        "bio": profile.bio,
        "mission_statement": profile.mission_statement,

        "church_name": profile.church_name,
        "church_logo": profile.church_logo,
        "church_size": profile.church_size,

        "ministry_focus": profile.ministry_focus,
        "specialties": profile.specialties,
        "denomination": profile.denomination,
        "years_in_ministry": profile.years_in_ministry,
        "ordination_year": profile.ordination_year,

        "location": profile.location,
        "city": profile.city,
        "state": profile.state,
        "country": profile.country,
        "time_zone": profile.time_zone,

        "website": profile.website,
        "phone": profile.phone,
        "email_public": profile.email_public,

        "facebook": profile.facebook,
        "youtube": profile.youtube,
        "instagram": profile.instagram,
        "twitter": profile.twitter,

        "profile_image": profile.profile_image,
        "cover_image": profile.cover_image,

        "favorite_scripture": profile.favorite_scripture,
        "languages": profile.languages,
        "service_times": profile.service_times,

        "accepts_prayer_requests": profile.accepts_prayer_requests,
        "allow_direct_messages": profile.allow_direct_messages,
        "is_verified": profile.is_verified,
        "is_public": profile.is_public,
        "visibility": profile.visibility,
        "slug": profile.slug,

        "created_at": profile.created_at,
        "updated_at": profile.updated_at
    }


def apply_profile_updates(profile: PastorProfile, data: dict):
    """
    Apply validated updates to a pastor profile.
    """

    allowed_fields = [
        "bio",
        "mission_statement",

        "church_name",
        "church_logo",
        "church_size",

        "ministry_focus",
        "specialties",
        "denomination",
        "years_in_ministry",
        "ordination_year",

        "location",
        "city",
        "state",
        "country",
        "time_zone",

        "website",
        "phone",
        "email_public",

        "facebook",
        "youtube",
        "instagram",
        "twitter",

        "profile_image",
        "cover_image",

        "favorite_scripture",
        "languages",
        "service_times",

        "accepts_prayer_requests",
        "allow_direct_messages",

        # Backward compatibility
        "is_public",

        # New visibility model
        "visibility",

        "slug"
    ]

    # =====================================
    # VALIDATE PROFILE VISIBILITY
    # =====================================
    if "visibility" in data:

        allowed_visibility = {
            "public",
            "members",
            "private"
        }

        visibility = (
            str(data["visibility"])
            .strip()
            .lower()
        )

        if visibility not in allowed_visibility:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid visibility. "
                    "Must be 'public', "
                    "'members', or 'private'."
                )
            )

        data["visibility"] = visibility

        # Keep old boolean field synchronized
        profile.is_public = (
            visibility != "private"
        )

    # =====================================
    # APPLY UPDATES
    # =====================================
    for field in allowed_fields:

        if field in data:

            setattr(
                profile,
                field,
                data[field]
            )


def can_view_profile(
    profile: PastorProfile,
    viewer: User | None,
    owner: User
):
    visibility = profile.visibility or "public"

    # Public profiles are visible to everyone
    if visibility == "public":
        return True

    # Owner can always view
    if viewer and viewer.id == owner.id:
        return True

    # Admins can always view
    if viewer and viewer.role == "admin":
        return True

    # Members-only profiles require login
    if visibility == "members":
        return viewer is not None

    # Private profiles are owner/admin only
    if visibility == "private":
        return False

    return False

@router.get("/me")
def get_my_profile(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    current_user = get_current_user_from_header(
        authorization,
        db
    )

    if current_user.role not in ["pastor", "admin"]:
        raise HTTPException(
        status_code=403,
        detail="Only pastors or administrators have pastor profiles"
    )

    profile = db.query(PastorProfile).filter(
        PastorProfile.user_id == current_user.id
    ).first()

    if not profile:
        profile = PastorProfile(
            user_id=current_user.id
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile_to_dict(profile, current_user)


@router.put("/me")
def update_my_profile(
    data: dict,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    current_user = get_current_user_from_header(
        authorization,
        db
    )

    if current_user.role not in ["pastor", "admin"]:
        raise HTTPException(
        status_code=403,
        detail="Only pastors or administrators can update pastor profiles"
    )

    profile = db.query(PastorProfile).filter(
        PastorProfile.user_id == current_user.id
    ).first()

    if not profile:
        profile = PastorProfile(
            user_id=current_user.id
        )
        db.add(profile)
        db.flush()

    apply_profile_updates(profile, data)

    db.commit()
    db.refresh(profile)

    return {
        "message": "Profile updated successfully",
        "profile": profile_to_dict(profile, current_user)
    }


# =========================
# PUBLIC PROFILE BY SLUG
# =========================
@router.get("/by-slug/{slug}")
def public_profile_by_slug(
    slug: str,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    profile = db.query(PastorProfile).filter(
        PastorProfile.slug == slug
    ).first()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Pastor profile not found"
        )

    pastor = db.query(User).filter(
        User.id == profile.user_id,
        User.role.in_(["pastor", "admin"])
    ).first()

    if not pastor:
        raise HTTPException(
            status_code=404,
            detail="Pastor not found"
        )

    viewer = get_optional_user_from_header(
        authorization,
        db
    )

    if not can_view_profile(profile, viewer, pastor):
        raise HTTPException(
            status_code=403,
            detail="This ministry profile is private."
        )

    follower_count = db.query(PastorFollower).filter(
        PastorFollower.pastor_id == pastor.id
    ).count()

    sermons = db.query(Sermon).filter(
        Sermon.author_id == pastor.id
    ).order_by(
        Sermon.created_at.desc()
    ).limit(10).all()

    result = profile_to_dict(profile, pastor)

    result["followers"] = follower_count

    result["sermons"] = [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at
        }
        for s in sermons
    ]

    return result

# =========================
# PUBLIC PROFILE
# =========================
@router.get("/{pastor_id}")
def public_profile(
    pastor_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    pastor = db.query(User).filter(
        User.id == pastor_id,
        User.role.in_(["pastor", "admin"])
    ).first()

    if not pastor:
        raise HTTPException(
            status_code=404,
            detail="Pastor not found"
        )

    profile = db.query(PastorProfile).filter(
        PastorProfile.user_id == pastor.id
    ).first()

    if not profile:
        profile = PastorProfile(
            user_id=pastor.id
        )

        db.add(profile)
        db.commit()
        db.refresh(profile)

    # =====================================
    # PROFILE VISIBILITY CHECK
    # =====================================
    viewer = get_optional_user_from_header(
        authorization,
        db
    )

    if not can_view_profile(
        profile,
        viewer,
        pastor
    ):
        raise HTTPException(
            status_code=403,
            detail="This ministry profile is private."
        )

    follower_count = db.query(PastorFollower).filter(
        PastorFollower.pastor_id == pastor.id
    ).count()

    sermons = db.query(Sermon).filter(
        Sermon.author_id == pastor.id
    ).order_by(
        Sermon.created_at.desc()
    ).limit(10).all()

    result = profile_to_dict(
        profile,
        pastor
    )

    result["followers"] = follower_count

    result["sermons"] = [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at
        }
        for s in sermons
    ]

    return result