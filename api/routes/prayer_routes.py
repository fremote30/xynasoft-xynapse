from fastapi import (
    APIRouter,
    Depends,
    HTTPException
)

from sqlalchemy.orm import Session

from api.db.database import get_db

from api.models.prayer import Prayer

from api.core.dependencies import (
    get_current_user
)

router = APIRouter()


# =====================================
# CREATE PRAYER
# =====================================
@router.post("/prayers")
def create_prayer(
    payload: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    message = payload.get("message")

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Prayer message required"
        )

    prayer = Prayer(
        message=message,
        user_id=user.id,
        user_name=user.name
    )

    db.add(prayer)

    db.commit()

    db.refresh(prayer)

    return {
        "success": True
    }


# =====================================
# RECENT PRAYERS
# =====================================
@router.get("/dashboard/recent-prayers")
def recent_prayers(
    db: Session = Depends(get_db)
):

    prayers = (
        db.query(Prayer)
        .order_by(
            Prayer.created_at.desc()
        )
        .limit(10)
        .all()
    )

    return [
        {
            "id": p.id,
            "message": p.message,
            "user_name": p.user_name,
            "created_at": p.created_at
        }
        for p in prayers
    ]


# =====================================
# MEMBER PRAYERS
# =====================================
@router.get("/dashboard/member-prayers")
def member_prayers(
    db: Session = Depends(get_db)
):

    prayers = (
        db.query(Prayer)
        .order_by(
            Prayer.created_at.desc()
        )
        .limit(10)
        .all()
    )

    return [
        {
            "id": p.id,
            "message": p.message,
            "user_name": p.user_name,
            "created_at": p.created_at
        }
        for p in prayers
    ]