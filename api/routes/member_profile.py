from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException
)

from sqlalchemy.orm import Session

from api.core.security import decode_token
from api.db.database import SessionLocal
from api.models.member_profile import MemberProfile
from api.models.user import User

from api.models.follow import PastorFollower
from api.models.prayer import Prayer, PrayerBookmark

from datetime import datetime
from api.models.member_recent_sermon import MemberRecentSermon
from api.models.sermon import Sermon
from datetime import datetime, timezone

router = APIRouter(
    prefix="/member-profile",
    tags=["Member Profiles"]
)


# =====================================
# DATABASE
# =====================================
def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# =====================================
# REQUIRED AUTHENTICATED USER
# =====================================
def get_current_user_from_header(
    authorization: str,
    db: Session
):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing token"
        )

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Invalid token payload"
        )

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=401,
            detail="Invalid user ID"
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user


# =====================================
# OPTIONAL AUTHENTICATED USER
# =====================================
def get_optional_user_from_header(
    authorization: str | None,
    db: Session
):
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)

    if not payload:
        return None

    user_id = payload.get("sub")

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    return db.query(User).filter(
        User.id == user_id
    ).first()


# =====================================
# SERIALIZER
# =====================================
def member_profile_to_dict(
    profile: MemberProfile,
    user: User,
    include_private: bool = False
):
    result = {
        "id": profile.id,
        "user_id": user.id,
        "name": user.name,
        "role": user.role,

        "bio": profile.bio or "",
        "profile_image": profile.profile_image or "",
        "favorite_scripture": profile.favorite_scripture or "",

        "city": profile.city or "",
        "state": profile.state or "",
        "country": profile.country or "",
        "languages": profile.languages or "",

        "church_name": profile.church_name or "",
        "ministry_interests": profile.ministry_interests or "",
        "prayer_interests": profile.prayer_interests or "",

        "visibility": profile.visibility or "members",

        "allow_direct_messages": (
            profile.allow_direct_messages
            if profile.allow_direct_messages is not None
            else True
        ),

        "slug": profile.slug or "",

        "created_at": profile.created_at,
        "updated_at": profile.updated_at
    }

    if include_private:
        result["email"] = user.email

        result["receive_notifications"] = (
            profile.receive_notifications
            if profile.receive_notifications is not None
            else True
        )

    return result


# =====================================
# APPLY PROFILE UPDATES
# =====================================
def apply_member_profile_updates(
    profile: MemberProfile,
    data: dict
):
    allowed_fields = [
        "bio",
        "profile_image",
        "favorite_scripture",

        "city",
        "state",
        "country",
        "languages",

        "church_name",
        "ministry_interests",
        "prayer_interests",

        "visibility",
        "allow_direct_messages",
        "receive_notifications",

        "slug"
    ]

    if "visibility" in data:
        visibility = str(
            data.get("visibility") or ""
        ).strip().lower()

        allowed_visibility = {
            "public",
            "members",
            "private"
        }

        if visibility not in allowed_visibility:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid visibility. "
                    "Must be 'public', 'members', or 'private'."
                )
            )

        data["visibility"] = visibility

    if "slug" in data:
        slug = str(
            data.get("slug") or ""
        ).strip().lower()

        data["slug"] = slug or None

    for field in allowed_fields:
        if field in data:
            setattr(
                profile,
                field,
                data[field]
            )


# =====================================
# VISIBILITY PERMISSION
# =====================================
def can_view_member_profile(
    profile: MemberProfile,
    viewer: User | None,
    owner: User
):
    visibility = profile.visibility or "members"

    if viewer and viewer.id == owner.id:
        return True

    if viewer and viewer.role == "admin":
        return True

    if visibility == "public":
        return True

    if visibility == "members":
        return viewer is not None

    if visibility == "private":
        return False

    return False


# =====================================
# GET MY MEMBER PROFILE
# =====================================
@router.get("/me")
def get_my_member_profile(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    current_user = get_current_user_from_header(
        authorization,
        db
    )

    if current_user.role != "member":
        raise HTTPException(
            status_code=403,
            detail="Only members have member profiles"
        )

    profile = db.query(MemberProfile).filter(
        MemberProfile.user_id == current_user.id
    ).first()

    if not profile:
        profile = MemberProfile(
            user_id=current_user.id,
            visibility="members",
            allow_direct_messages=True,
            receive_notifications=True
        )

        db.add(profile)
        db.commit()
        db.refresh(profile)

    return member_profile_to_dict(
        profile,
        current_user,
        include_private=True
    )


# =====================================
# UPDATE MY MEMBER PROFILE
# =====================================
@router.put("/me")
def update_my_member_profile(
    data: dict,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    current_user = get_current_user_from_header(
        authorization,
        db
    )

    if current_user.role != "member":
        raise HTTPException(
            status_code=403,
            detail="Only members can update member profiles"
        )

    profile = db.query(MemberProfile).filter(
        MemberProfile.user_id == current_user.id
    ).first()

    if not profile:
        profile = MemberProfile(
            user_id=current_user.id,
            visibility="members",
            allow_direct_messages=True,
            receive_notifications=True
        )

        db.add(profile)
        db.flush()

    incoming_slug = str(
        data.get("slug") or ""
    ).strip().lower()

    if incoming_slug:
        existing_slug = db.query(MemberProfile).filter(
            MemberProfile.slug == incoming_slug,
            MemberProfile.user_id != current_user.id
        ).first()

        if existing_slug:
            raise HTTPException(
                status_code=409,
                detail="This member profile slug is already in use"
            )

    apply_member_profile_updates(
        profile,
        data
    )

    db.commit()
    db.refresh(profile)

    return {
        "message": "Member profile updated successfully",
        "profile": member_profile_to_dict(
            profile,
            current_user,
            include_private=True
        )
    }

# =====================================
# MEMBER ACTIVITY SUMMARY
# =====================================
@router.get("/me/activity")
def get_member_activity(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    current_user = get_current_user_from_header(
        authorization,
        db
    )

    if current_user.role != "member":
        raise HTTPException(
            status_code=403,
            detail="Only members can view member activity"
        )

    following_pastors = db.query(
        PastorFollower
    ).filter(
        PastorFollower.member_id == current_user.id
    ).count()

    prayer_requests = db.query(
        Prayer
    ).filter(
        Prayer.user_id == current_user.id,
        Prayer.is_hidden == False
    ).count()

    answered_prayers = db.query(
        Prayer
    ).filter(
        Prayer.user_id == current_user.id,
        Prayer.is_hidden == False,
        Prayer.status == "answered"
    ).count()

    saved_prayers = db.query(
        PrayerBookmark
    ).filter(
        PrayerBookmark.user_id == current_user.id
    ).count()

    return {
        "following_pastors": following_pastors,
        "saved_sermons": 0,
        "prayer_requests": prayer_requests,
        "answered_prayers": answered_prayers,
        "saved_prayers": saved_prayers
    }


# =====================================
# SAVE RECENTLY OPENED SERMON
# =====================================
@router.post("/recent-sermon/{sermon_id}")
def save_recent_sermon(
    sermon_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    current_user = get_current_user_from_header(
        authorization,
        db
    )

    if current_user.role != "member":
        raise HTTPException(
            status_code=403,
            detail="Only members can save recent sermons"
        )

    sermon = db.query(Sermon).filter(
        Sermon.id == sermon_id
    ).first()

    if not sermon:
        raise HTTPException(
            status_code=404,
            detail="Sermon not found"
        )

    if not sermon.is_public:
        raise HTTPException(
            status_code=403,
            detail="This sermon is not publicly available"
        )

    recent = db.query(MemberRecentSermon).filter(
        MemberRecentSermon.member_id == current_user.id,
        MemberRecentSermon.sermon_id == sermon.id
    ).first()

    if recent:
        recent.last_opened_at = datetime.now(timezone.utc)
    else:
        recent = MemberRecentSermon(
            member_id=current_user.id,
            sermon_id=sermon.id,
            last_opened_at=datetime.now(timezone.utc)
        )

        db.add(recent)

    db.commit()
    db.refresh(recent)

    return {
        "success": True,
        "message": "Recent sermon updated",
        "sermon_id": sermon.id,
        "last_opened_at": recent.last_opened_at
    }


# =====================================
# GET MOST RECENT SERMON
# =====================================
@router.get("/recent-sermon")
def get_recent_sermon(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    current_user = get_current_user_from_header(
        authorization,
        db
    )

    if current_user.role != "member":
        raise HTTPException(
            status_code=403,
            detail="Only members can view recent sermons"
        )

    recent = (
        db.query(MemberRecentSermon)
        .filter(
            MemberRecentSermon.member_id == current_user.id
        )
        .order_by(
            MemberRecentSermon.last_opened_at.desc()
        )
        .first()
    )

    if not recent:
        return {
            "success": True,
            "sermon": None
        }

    sermon = db.query(Sermon).filter(
        Sermon.id == recent.sermon_id
    ).first()

    if not sermon or not sermon.is_public:
        return {
            "success": True,
            "sermon": None
        }
    author_name = (
        sermon.author.name
        if sermon.author
        else ""
    )

    return {
        "success": True,
        "sermon": {
            "id": sermon.id,
            "title": sermon.title,
            "scripture": sermon.scripture,
            "content": sermon.content,
            "author_id": sermon.author_id,
            "author_name": author_name,
            "is_public": bool(sermon.is_public),
            "created_at": sermon.created_at,
            "updated_at": sermon.updated_at,
            "last_opened_at": recent.last_opened_at
        }
    }

# =====================================
# PUBLIC MEMBER PROFILE BY SLUG
# =====================================
@router.get("/by-slug/{slug}")
def public_member_profile_by_slug(
    slug: str,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    profile = db.query(MemberProfile).filter(
        MemberProfile.slug == slug
    ).first()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Member profile not found"
        )

    member = db.query(User).filter(
        User.id == profile.user_id,
        User.role == "member"
    ).first()

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Member not found"
        )

    viewer = get_optional_user_from_header(
        authorization,
        db
    )

    if not can_view_member_profile(
        profile,
        viewer,
        member
    ):
        raise HTTPException(
            status_code=403,
            detail="This member profile is private"
        )

    return member_profile_to_dict(
        profile,
        member
    )


# =====================================
# PUBLIC MEMBER PROFILE BY USER ID
# =====================================
@router.get("/{member_id}")
def public_member_profile(
    member_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    member = db.query(User).filter(
        User.id == member_id,
        User.role == "member"
    ).first()

    if not member:
        raise HTTPException(
            status_code=404,
            detail="Member not found"
        )

    profile = db.query(MemberProfile).filter(
        MemberProfile.user_id == member.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Member profile not found"
        )

    viewer = get_optional_user_from_header(
        authorization,
        db
    )

    if not can_view_member_profile(
        profile,
        viewer,
        member
    ):
        raise HTTPException(
            status_code=403,
            detail="This member profile is private"
        )

    return member_profile_to_dict(
        profile,
        member
    )

