from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from api.db.database import get_db
from api.models.shared_sermon import SharedSermon
from api.models.sermon import Sermon

# 🔥 CENTRAL AUTH
from api.core.dependencies import get_current_user

router = APIRouter()


# ================================
# 🔗 SHARE SERMON (SECURED)
# ================================
@router.post("/sermon/share")
def share_sermon(
    data: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    try:
        sermon_id = data.get("sermon_id")
        to_pastor_id = data.get("to_pastor_id")

        if not sermon_id or not to_pastor_id:
            raise HTTPException(status_code=400, detail="Missing required fields")

        # 🔒 Ensure sermon exists
        sermon = db.query(Sermon).filter(Sermon.id == sermon_id).first()
        if not sermon:
            raise HTTPException(status_code=404, detail="Sermon not found")

        # 🔒 Ensure ownership (optional but recommended)
        if sermon.author_id != user.id:
            raise HTTPException(status_code=403, detail="Not authorized to share this sermon")

        # 🔒 Prevent duplicate shares
        existing = db.query(SharedSermon).filter(
            SharedSermon.sermon_id == sermon_id,
            SharedSermon.from_pastor_id == user.id,
            SharedSermon.to_pastor_id == to_pastor_id
        ).first()

        if existing:
            return {"message": "Already shared"}

        shared = SharedSermon(
            sermon_id=sermon_id,
            from_pastor_id=user.id,  # 🔥 NEVER trust frontend
            to_pastor_id=to_pastor_id,
            comment=data.get("comment", ""),
            created_at=datetime.utcnow()
        )

        db.add(shared)
        db.commit()
        db.refresh(shared)

        return {
            "success": True,
            "share": {
                "id": shared.id,
                "sermon_id": shared.sermon_id,
                "from_pastor_id": shared.from_pastor_id,
                "to_pastor_id": shared.to_pastor_id,
                "comment": shared.comment,
                "created_at": shared.created_at
            }
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# 📥 GET SHARED WITH ME (SECURED)
# ================================
@router.get("/sermon/shared")
def get_shared(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    results = db.query(SharedSermon).filter(
        SharedSermon.to_pastor_id == user.id
    ).order_by(SharedSermon.created_at.desc()).all()

    return [
        {
            "id": r.id,
            "sermon_id": r.sermon_id,
            "from_pastor_id": r.from_pastor_id,
            "to_pastor_id": r.to_pastor_id,
            "comment": r.comment,
            "created_at": r.created_at
        }
        for r in results
    ]