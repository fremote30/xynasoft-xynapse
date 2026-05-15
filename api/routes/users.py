from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from api.db.database import SessionLocal

from api.models.user import User
from api.models.pastor_profile import PastorProfile

from api.core.security import decode_token


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
# =========================
@router.post("/upgrade-to-pastor")
def upgrade_to_pastor(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):

    # =========================
    # VALIDATE TOKEN
    # =========================
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

    # =========================
    # GET USER
    # =========================
    user = db.query(User).filter(
        User.id == int(user_id)
    ).first()

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # =========================
    # ALREADY PASTOR
    # =========================
    if user.role == "pastor":

        existing_profile = db.query(
            PastorProfile
        ).filter(
            PastorProfile.user_id == user.id
        ).first()

        # SAFETY PROFILE CREATION
        if not existing_profile:

            profile = PastorProfile(
                user_id=user.id
            )

            db.add(profile)
            db.commit()

        return {
            "message": "Already a pastor",
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role
            }
        }

    # =========================
    # UPGRADE ROLE
    # =========================
    user.role = "pastor"

    # =========================
    # CREATE PASTOR PROFILE
    # =========================
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

    # =========================
    # SAVE
    # =========================
    db.commit()

    db.refresh(user)

    return {
        "message": "Successfully upgraded to pastor",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }