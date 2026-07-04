from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from datetime import datetime

from api.db.database import SessionLocal
from api.models.user import User
from api.models.pastor_profile import PastorProfile
from api.core.security import decode_token

from api.core.dependencies import get_current_user
from api.models.sermon import Sermon


router = APIRouter(
    prefix="/users",
    tags=["Users"]
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

# UPGRADE TO PASTOR

# (SUBMIT APPLICATION)

# =========================

@router.post("/upgrade-to-pastor")
def upgrade_to_pastor(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):


    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Missing token"
        )

    token = authorization.split(" ")[1]

    payload = decode_token(token)

    if not payload or payload.get("type") != "access":
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

    if user.pastor_status == "approved":
        return {
            "message": "Already an approved pastor"
        }

    if user.pastor_status == "pending":
        return {
            "message": "Application already pending"
        }
    

    user.pastor_status = "pending"
    user.pastor_application_date = datetime.utcnow()

    db.commit()
    db.refresh(user)

    return {
        "message": "Pastor application submitted",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "pastor_status": user.pastor_status
        }
    }

# =========================

# PENDING PASTOR APPLICATIONS

# =========================

@router.get("/pastor-applications")
def get_pastor_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )       
    applications = db.query(User).filter(
        User.pastor_status == "pending"
    ).all()

    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "applied_at": user.pastor_application_date
        }
        for user in applications
    ]


# =========================

# APPROVE PASTOR

# =========================

@router.post("/{user_id}/approve-pastor")
def approve_pastor(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    user.pastor_review_date = datetime.utcnow()

    existing_profile = db.query(
        PastorProfile
    ).filter(
        PastorProfile.user_id == user.id
    ).first()

    if not existing_profile:

        profile = PastorProfile(
            user_id=user.id
        )

        db.add(profile)

    db.commit()

    return {
        "message": "Pastor approved"
    }

# =========================

# REJECT PASTOR

# =========================

@router.post("/{user_id}/reject-pastor")
def reject_pastor(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
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
    user.pastor_review_date = datetime.utcnow()

    db.commit()

    return {
        "message": "Pastor application rejected"
    }

@router.post("/{user_id}/make-admin")
def make_admin(
    user_id: int,
    db: Session = Depends(get_db)
):

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    user.role = "admin"

    db.commit()

    return {
        "message": "User promoted to admin"
    }

# =========================
# ADMIN STATS
# =========================

@router.get("/admin/stats")
def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required"
        )

    members = db.query(User).filter(
        User.role == "member"
    ).count()

    pastors = db.query(User).filter(
        User.role == "pastor"
    ).count()

    pending_applications = db.query(User).filter(
        User.pastor_status == "pending"
    ).count()

    sermons = db.query(Sermon).count()

    return {
        "members": members,
        "pastors": pastors,
        "pending_applications": pending_applications,
        "sermons": sermons
    }

# =========================
# USER SEARCH 2.0
# =========================
@router.get("/search")
def search_users(
    q: str,
    type: str = "all",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = q.strip()

    if len(query) < 2:
        return []

    users_query = db.query(User).filter(
        User.id != current_user.id,
        User.role.in_(["member", "pastor", "admin"]),
        (
            User.name.ilike(f"%{query}%") |
            User.email.ilike(f"%{query}%")
        )
    )

    if type == "pastor":
        users_query = users_query.filter(User.role == "pastor")

    elif type == "member":
        users_query = users_query.filter(User.role == "member")

    users = users_query.limit(20).all()

    results = []

    for user in users:
        profile = db.query(PastorProfile).filter(
            PastorProfile.user_id == user.id
        ).first()

        results.append({
            "id": user.id,
            "name": user.name or user.email,
            "email": user.email,
            "role": user.role,
            "pastor_status": user.pastor_status,
            "verified": user.role == "pastor" and user.pastor_status == "approved",
            "church": getattr(profile, "church_name", None) if profile else None,
            "city": getattr(profile, "city", None) if profile else None,
            "country": getattr(profile, "country", None) if profile else None,
            "avatar": getattr(profile, "profile_image_url", None) if profile else None
        })

    return results
