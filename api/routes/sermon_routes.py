from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import json

from api.db.database import get_db
from api.models.sermon import Sermon
from api.core.dependencies import get_current_user

router = APIRouter()

# =========================================
# SAVE SERMON
# =========================================
@router.post("/sermon/save")
def save_sermon(
    data: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    if not data:
        raise HTTPException(
            status_code=400,
            detail="Sermon data is required"
        )

    # =====================================
    # TITLE
    # =====================================
    title = data.get(
        "title",
        "Untitled Sermon"
    )

    # =====================================
    # STORE FULL JSON
    # =====================================
    content = json.dumps(data)

    sermon = Sermon(
        author_id=user.id,
        title=title,
        content=content,
        created_at=datetime.utcnow()
    )

    db.add(sermon)
    db.commit()
    db.refresh(sermon)

    return {
        "message": "Sermon saved",
        "id": sermon.id
    }


# =========================================
# GET MY SERMONS
# =========================================
@router.get("/sermon/my")
def get_my_sermons(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    sermons = (
        db.query(Sermon)
        .filter(
            Sermon.author_id == user.id
        )
        .order_by(
            Sermon.created_at.desc()
        )
        .all()
    )

    results = []

    for sermon in sermons:

        try:

            parsed_content = json.loads(
                sermon.content
            )

        except:

            parsed_content = {
                "title": sermon.title,
                "content": sermon.content
            }

        results.append({

            "id":
                sermon.id,

            "title":
                sermon.title,

            "content":
                parsed_content,

            "created_at":
                sermon.created_at,

            "updated_at":
                sermon.updated_at,

            "views":
                sermon.views or 0,

            "shares":
                sermon.shares or 0
        })

    return results


# =========================================
# GET SINGLE SERMON
# =========================================
@router.get("/sermon/{sermon_id}")
def get_sermon(
    sermon_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    sermon = (
        db.query(Sermon)
        .filter(
            Sermon.id == sermon_id
        )
        .first()
    )

    if not sermon:

        raise HTTPException(
            status_code=404,
            detail="Sermon not found"
        )

    # =====================================
    # OWNER CHECK
    # =====================================
    if sermon.author_id != user.id:

        raise HTTPException(
            status_code=403,
            detail="Not authorized"
        )

    # =====================================
    # TRACK VIEW
    # =====================================
    try:

        sermon.views = (
            sermon.views or 0
        ) + 1

        db.commit()
        db.refresh(sermon)

    except Exception as e:

        print(
            "View tracking error:",
            e
        )

    # =====================================
    # PARSE STRUCTURED JSON
    # =====================================
    try:

        parsed_content = json.loads(
            sermon.content
        )

    except:

        parsed_content = {
            "title": sermon.title,
            "content": sermon.content
        }

    return {

        "id":
            sermon.id,

        "title":
            sermon.title,

        "content":
            parsed_content,

        "created_at":
            sermon.created_at,

        "updated_at":
            sermon.updated_at,

        "views":
            sermon.views or 0,

        "shares":
            sermon.shares or 0
    }


# =========================================
# UPDATE SERMON
# =========================================
@router.put("/sermon/update/{sermon_id}")
def update_sermon(
    sermon_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    sermon = (
        db.query(Sermon)
        .filter(
            Sermon.id == sermon_id
        )
        .first()
    )

    if not sermon:

        raise HTTPException(
            status_code=404,
            detail="Sermon not found"
        )

    if sermon.author_id != user.id:

        raise HTTPException(
            status_code=403,
            detail="Not authorized"
        )

    # =====================================
    # UPDATE TITLE
    # =====================================
    if "title" in data:

        sermon.title = data["title"]

    # =====================================
    # UPDATE FULL JSON
    # =====================================
    sermon.content = json.dumps(data)

    sermon.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(sermon)

    return {
        "message":
            "Updated successfully"
    }


# =========================================
# DELETE SERMON
# =========================================
@router.delete("/sermon/{sermon_id}")
def delete_sermon(
    sermon_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    sermon = (
        db.query(Sermon)
        .filter(
            Sermon.id == sermon_id
        )
        .first()
    )

    if not sermon:

        raise HTTPException(
            status_code=404,
            detail="Sermon not found"
        )

    if sermon.author_id != user.id:

        raise HTTPException(
            status_code=403,
            detail="Not authorized"
        )

    db.delete(sermon)
    db.commit()

    return {
        "message":
            "Sermon deleted successfully"
    }