# LEGACY / FUTURE ROUTES
# Not currently used by frontend.


from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from api.db.database import SessionLocal
from api.models.user import User
from api.models.follow import PastorFollower

from api.core.security import decode_token
from datetime import datetime

router = APIRouter(
    prefix="/pastors",
    tags=["Pastors"]
)


# =========================
# DATABASE SESSION
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

# APPLY FOR PASTOR

# =========================

@router.post("/apply")
def apply_for_pastor(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):


    current_user = get_current_user(
        authorization,
        db
    )

    # Already pastor
    if current_user.role == "pastor":
        raise HTTPException(
            status_code=400,
            detail="Already a pastor"
        )

    # Already pending
    if current_user.pastor_status == "pending":
        raise HTTPException(
            status_code=400,
            detail="Application already pending"
        )

    current_user.pastor_status = "pending"

    current_user.pastor_application_date = (
        datetime.utcnow()
    )

    db.commit()

    return {
        "message":
        "Pastor application submitted successfully"
    }


# =========================
# GET ALL PASTORS
# =========================
@router.get("/")
def get_pastors(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):

    current_user = None

    # OPTIONAL AUTH
    if authorization and authorization.startswith("Bearer "):

        token = authorization.split(" ")[1]

        payload = decode_token(token)

        if payload:

            user_id = payload.get("sub")

            current_user = db.query(User).filter(
                User.id == int(user_id)
            ).first()

    # =========================
    # GET ALL PASTORS
    # =========================
    pastors = db.query(User).filter(
        User.role == "pastor"
    ).all()

    results = []

    for pastor in pastors:

        follower_count = db.query(
            PastorFollower
        ).filter(
            PastorFollower.pastor_id == pastor.id
        ).count()

        is_following = False

        if current_user and current_user.role == "member":

            existing = db.query(
                PastorFollower
            ).filter(
                PastorFollower.member_id == current_user.id,
                PastorFollower.pastor_id == pastor.id
            ).first()

            is_following = existing is not None

        results.append({
            "id": pastor.id,
            "name": pastor.name,
            "email": pastor.email,
            "followers": follower_count,
            "is_following": is_following
        })

    return results


# =========================
# FOLLOW PASTOR
# =========================
@router.post("/{pastor_id}/follow")
def follow_pastor(
    pastor_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):

    current_user = get_current_user(
        authorization,
        db
    )

    # ONLY MEMBERS
    if current_user.role != "member":
        raise HTTPException(
            status_code=403,
            detail="Only members can follow pastors"
        )

    # FIND PASTOR
    pastor = db.query(User).filter(
        User.id == pastor_id,
        User.role == "pastor"
    ).first()

    if not pastor:
        raise HTTPException(
            status_code=404,
            detail="Pastor not found"
        )

    # PREVENT SELF FOLLOW
    if current_user.id == pastor.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot follow yourself"
        )

    # CHECK EXISTING
    existing = db.query(
        PastorFollower
    ).filter(
        PastorFollower.member_id == current_user.id,
        PastorFollower.pastor_id == pastor.id
    ).first()

    if existing:

        return {
            "message": "Already following"
        }

    # CREATE FOLLOW
    follow = PastorFollower(
        member_id=current_user.id,
        pastor_id=pastor.id
    )

    db.add(follow)
    db.commit()

    return {
        "message": "Pastor followed successfully"
    }


# =========================
# UNFOLLOW PASTOR
# =========================
@router.delete("/{pastor_id}/unfollow")
def unfollow_pastor(
    pastor_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):

    current_user = get_current_user(
        authorization,
        db
    )

    follow = db.query(
        PastorFollower
    ).filter(
        PastorFollower.member_id == current_user.id,
        PastorFollower.pastor_id == pastor_id
    ).first()

    if not follow:
        raise HTTPException(
            status_code=404,
            detail="Follow relationship not found"
        )

    db.delete(follow)
    db.commit()

    return {
        "message": "Pastor unfollowed successfully"
    }

# =========================
# MEMBER FEED
# =========================
@router.get("/feed")
def member_feed(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):

    current_user = get_current_user(
        authorization,
        db
    )

    # ONLY MEMBERS
    if current_user.role != "member":
        raise HTTPException(
            status_code=403,
            detail="Only members have feeds"
        )

    # =========================
    # GET FOLLOWED PASTORS
    # =========================
    follows = db.query(
        PastorFollower
    ).filter(
        PastorFollower.member_id == current_user.id
    ).all()

    pastor_ids = [
        f.pastor_id
        for f in follows
    ]

    # =========================
    # NO FOLLOWS
    # =========================
    if not pastor_ids:
        return []

    # =========================
    # GET SERMONS
    # =========================
    from api.models.sermon import Sermon

    sermons = db.query(Sermon).filter(
        Sermon.author_id.in_(pastor_ids)
    ).order_by(
        Sermon.created_at.desc()
    ).limit(20).all()

    results = []

    for sermon in sermons:

        pastor = db.query(User).filter(
            User.id == sermon.author_id
        ).first()

        results.append({
            "id": sermon.id,
            "title": sermon.title,
            "content": sermon.content[:200],
            "created_at": sermon.created_at,
            "pastor_name": pastor.name if pastor else "Unknown"
        })

    return results

# =========================
# PENDING APPLICATIONS
# ADMIN ONLY
# =========================
@router.get("/pending")
def get_pending_applications(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):

    current_user = get_current_user(
        authorization,
        db
    )

    if current_user.role != "admin":

        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    applications = db.query(User).filter(
        User.pastor_status == "pending"
    ).order_by(
        User.pastor_application_date.desc()
    ).all()

    results = []

    for user in applications:

        results.append({

            "id": user.id,

            "name": user.name,

            "email": user.email,

            "pastor_status":
                user.pastor_status,

            "applied_at":
                user.pastor_application_date
        })

    return results

# =========================
# APPROVE PASTOR
# ADMIN ONLY
# =========================
@router.post("/approve/{user_id}")
def approve_pastor(
    user_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):

    current_user = get_current_user(
        authorization,
        db
    )

    if current_user.role != "admin":

        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.role = "pastor"

    user.pastor_status = "approved"

    user.pastor_review_date = (
        datetime.utcnow()
    )

    db.commit()

    return {
        "message":
            "Pastor approved successfully"
    }

# =========================
# REJECT PASTOR
# ADMIN ONLY
# =========================
@router.post("/reject/{user_id}")
def reject_pastor(
    user_id: int,
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):

    current_user = get_current_user(
        authorization,
        db
    )

    if current_user.role != "admin":

        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:

        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.pastor_status = "rejected"

    user.pastor_review_date = (
        datetime.utcnow()
    )

    db.commit()

    return {
        "message":
            "Application rejected"
    }