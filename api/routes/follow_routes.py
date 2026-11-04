from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.models.user import User
from api.models.pastor_member import PastorMember
from api.models.sermon import Sermon

# 🔥 USE CENTRAL AUTH (CRITICAL)
from api.core.dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["Follow System"])


# =========================
# 🔹 FOLLOW PASTOR
# =========================
@router.post("/follow/{pastor_id}")
def follow_pastor(
    pastor_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if user.id == pastor_id:
        raise HTTPException(status_code=400, detail="Cannot follow yourself")

    pastor = db.query(User).filter(User.id == pastor_id).first()

    if not pastor:
        raise HTTPException(status_code=404, detail="Pastor not found")

    existing = db.query(PastorMember).filter(
        PastorMember.pastor_id == pastor_id,
        PastorMember.member_id == user.id
    ).first()

    if existing:
        return {"message": "Already following"}

    follow = PastorMember(
        pastor_id=pastor_id,
        member_id=user.id
    )

    db.add(follow)
    db.commit()

    return {"message": "Followed successfully"}


# =========================
# 🔹 UNFOLLOW
# =========================
@router.delete("/unfollow/{pastor_id}")
def unfollow_pastor(
    pastor_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    follow = db.query(PastorMember).filter(
        PastorMember.pastor_id == pastor_id,
        PastorMember.member_id == user.id
    ).first()

    if not follow:
        raise HTTPException(status_code=404, detail="Not following")

    db.delete(follow)
    db.commit()

    return {"message": "Unfollowed"}


# =========================
# 🔹 GET MY PASTORS
# =========================
@router.get("/my-pastors")
def get_my_pastors(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    follows = db.query(PastorMember).filter(
        PastorMember.member_id == user.id
    ).all()

    pastor_ids = [f.pastor_id for f in follows]

    if not pastor_ids:
        return []

    pastors = db.query(User).filter(User.id.in_(pastor_ids)).all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "email": p.email
        }
        for p in pastors
    ]


# =========================
# 🔹 DISCOVER PASTORS (PUBLIC)
# =========================
@router.get("/pastors")
def get_pastors(db: Session = Depends(get_db)):

    pastors = db.query(User).filter(User.role == "pastor").all()

    return [
        {
            "id": p.id,
            "name": p.name,
            "email": p.email
        }
        for p in pastors
    ]


# =========================
# 🔥 FEED (CORE FEATURE)
# =========================
@router.get("/feed")
def get_feed(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    follows = db.query(PastorMember).filter(
        PastorMember.member_id == user.id
    ).all()

    pastor_ids = [f.pastor_id for f in follows]

    if not pastor_ids:
        return []

    sermons = db.query(Sermon).filter(
        Sermon.author_id.in_(pastor_ids),
        Sermon.is_public == True
    ).order_by(Sermon.created_at.desc()).all()

    return [
        {
            "id": s.id,
            "title": s.title,
            "created_at": s.created_at,
            "author_id": s.author_id
        }
        for s in sermons
    ]