from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Header
)

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


# =========================
# DB
# =========================
def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# =========================
# GET CURRENT USER
# =========================
def get_current_user(
    authorization: str,
    db: Session
):

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing token"
        )

    token = authorization.split(" ")[1]

    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )

    user_id = payload.get("sub")

    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user


# =========================
# GET MY PROFILE
# =========================
@router.get("/me")
def get_my_profile(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):

    current_user = get_current_user(
        authorization,
        db
    )

    if current_user.role != "pastor":
        raise HTTPException(
            status_code=403,
            detail="Only pastors have profiles"
        )

    profile = db.query(
        PastorProfile
    ).filter(
        PastorProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found"
        )

    return {
        "id": profile.id,
        "user_id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "bio": profile.bio,
        "church_name": profile.church_name,
        "ministry_focus": profile.ministry_focus,
        "location": profile.location,
        "website": profile.website,
        "profile_image": profile.profile_image,
        "cover_image": profile.cover_image
    }


# =========================
# UPDATE MY PROFILE
# =========================
@router.put("/me")
def update_my_profile(
    data: dict,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):

    current_user = get_current_user(
        authorization,
        db
    )

    profile = db.query(
        PastorProfile
    ).filter(
        PastorProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Profile not found"
        )

    profile.bio = data.get(
        "bio",
        profile.bio
    )

    profile.church_name = data.get(
        "church_name",
        profile.church_name
    )

    profile.ministry_focus = data.get(
        "ministry_focus",
        profile.ministry_focus
    )

    profile.location = data.get(
        "location",
        profile.location
    )

    profile.website = data.get(
        "website",
        profile.website
    )

    profile.profile_image = data.get(
        "profile_image",
        profile.profile_image
    )

    profile.cover_image = data.get(
        "cover_image",
        profile.cover_image
    )

    db.commit()

    return {
        "message": "Profile updated successfully"
    }


# =========================
# PUBLIC PROFILE
# =========================
@router.get("/{pastor_id}")
def public_profile(
    pastor_id: int,
    db: Session = Depends(get_db)
):

    pastor = db.query(User).filter(
        User.id == pastor_id,
        User.role == "pastor"
    ).first()

    if not pastor:
        raise HTTPException(
            status_code=404,
            detail="Pastor not found"
        )

    profile = db.query(
        PastorProfile
    ).filter(
        PastorProfile.user_id == pastor.id
    ).first()

    follower_count = db.query(
        PastorFollower
    ).filter(
        PastorFollower.pastor_id == pastor.id
    ).count()

    sermons = db.query(
        Sermon
    ).filter(
        Sermon.author_id == pastor.id
    ).order_by(
        Sermon.created_at.desc()
    ).limit(10).all()

    return {
        "id": pastor.id,
        "name": pastor.name,
        "bio": profile.bio if profile else "",
        "church_name": profile.church_name if profile else "",
        "ministry_focus": profile.ministry_focus if profile else "",
        "location": profile.location if profile else "",
        "website": profile.website if profile else "",
        "profile_image": profile.profile_image if profile else "",
        "cover_image": profile.cover_image if profile else "",
        "followers": follower_count,
        "sermons": [
            {
                "id": s.id,
                "title": s.title,
                "created_at": s.created_at
            }
            for s in sermons
        ]
    }