from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from api.db.database import get_db
from api.models.sermon_comment import SermonComment

# 🔥 CENTRAL AUTH
from api.core.dependencies import get_current_user

router = APIRouter()


# =========================
# ➕ ADD COMMENT (SECURED)
# =========================
@router.post("/sermon/comment")
def add_comment(
    data: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    if not data.get("sermon_id") or not data.get("comment"):
        raise HTTPException(status_code=400, detail="Missing fields")

    comment = SermonComment(
        sermon_id=data["sermon_id"],
        pastor_id=user.id,  # 🔥 NEVER trust frontend
        comment=data["comment"],
        created_at=datetime.utcnow()
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

    return {
        "success": True,
        "comment": {
            "id": comment.id,
            "sermon_id": comment.sermon_id,
            "pastor_id": comment.pastor_id,
            "comment": comment.comment,
            "created_at": comment.created_at
        }
    }


# =========================
# 📖 GET COMMENTS (SECURED)
# =========================
@router.get("/sermon/comments/{sermon_id}")
def get_comments(
    sermon_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)  # 🔥 optional but recommended
):

    comments = db.query(SermonComment).filter(
        SermonComment.sermon_id == sermon_id
    ).order_by(SermonComment.created_at.desc()).all()

    return [
        {
            "id": c.id,
            "sermon_id": c.sermon_id,
            "pastor_id": c.pastor_id,
            "comment": c.comment,
            "created_at": c.created_at
        }
        for c in comments
    ]