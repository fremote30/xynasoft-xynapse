from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import json

from api.db.database import get_db
from api.models.sermon import Sermon
from api.services.ai_service import generate_ai_response
from api.core.dependencies import get_current_user  # 🔥 FIXED IMPORT

router = APIRouter()


# =========================
# PROMPT BUILDER (UNCHANGED)
# =========================
def build_prompt(data: dict):

    mode = data.get("mode", "default")
    variation = data.get("variation", 0)

    base_input = data.get("input", "")
    bible = data.get("bible", "")
    theme = data.get("theme", "")

    variations = [
        "Make it deeply theological and scripture-rich.",
        "Make it practical, relatable, and applicable to daily life.",
        "Make it inspirational, emotional, and powerful for preaching."
    ]

    variation_instruction = variations[variation] if variation < len(variations) else ""

    if mode == "scripture":
        mode_instruction = f"Expand and build a sermon based on this scripture:\n{bible}"

    elif mode == "topic":
        mode_instruction = f"Expand this topic into a sermon:\n{theme}"

    elif mode == "life":
        mode_instruction = f"Address this life situation pastorally:\n{base_input}"

    elif mode == "rewrite":
        mode_instruction = f"Refine and improve this sermon:\n{base_input}"

    elif mode == "notes":
        mode_instruction = f"Convert this rough message into a structured sermon:\n{base_input}"

    else:
        mode_instruction = f"Expand and organize this message into a sermon:\n{base_input}"

    return f"""
You are a Holy Spirit-led Christian sermon assistant.

- Do NOT replace the pastor’s voice
- Expand and strengthen message
- {variation_instruction}

Return ONLY valid JSON.

{mode_instruction}
"""


# =========================
# 🔒 GENERATE SERMON (NOW PROTECTED)
# =========================
@router.post("/sermon/generate")
def generate_sermon(
    data: dict,
    user=Depends(get_current_user)  # 🔥 LOCKED
):
    prompt = build_prompt(data)
    response = generate_ai_response(prompt)

    try:
        parsed = json.loads(response)

        parsed.setdefault("title", "")
        parsed.setdefault("main_message", "")
        parsed.setdefault("scripture", [])
        parsed.setdefault("introduction", "")
        parsed.setdefault("outline", [])
        parsed.setdefault("closing", "")
        parsed.setdefault("prayer", "")

        return parsed

    except:
        return {
            "title": "Draft Sermon",
            "main_message": data.get("input", ""),
            "scripture": [],
            "introduction": response[:500],
            "outline": [],
            "closing": "",
            "prayer": ""
        }


# =========================
# 🔒 SAVE SERMON
# =========================
@router.post("/sermon/save")
def save_sermon(
    data: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    if not data.get("content"):
        raise HTTPException(status_code=400, detail="Content is required")

    content = data.get("content")

    if isinstance(content, dict):
        content = json.dumps(content)

    sermon = Sermon(
        author_id=user.id,
        title=data.get("title", "Untitled Sermon"),
        content=content,
        created_at=datetime.utcnow()
    )

    db.add(sermon)
    db.commit()
    db.refresh(sermon)

    return {"message": "Sermon saved", "id": sermon.id}


# =========================
# 🔒 GET MY SERMONS
# =========================
@router.get("/sermon/my")
def get_my_sermons(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    return (
        db.query(Sermon)
        .filter(Sermon.author_id == user.id)
        .order_by(Sermon.created_at.desc())
        .all()
    )


# =========================
# 🔒 GET SINGLE SERMON (OWNER ONLY)
# =========================
@router.get("/sermon/{sermon_id}")
def get_sermon(
    sermon_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    sermon = db.query(Sermon).filter(Sermon.id == sermon_id).first()

    if not sermon:
        raise HTTPException(status_code=404, detail="Sermon not found")

    # 🔥 OWNER CHECK
    if sermon.author_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        sermon.views = (sermon.views or 0) + 1
        db.commit()
        db.refresh(sermon)
    except:
        pass

    try:
        sermon.content = json.loads(sermon.content)
    except:
        pass

    return sermon


# =========================
# 🔒 UPDATE SERMON (OWNER ONLY)
# =========================
@router.put("/sermon/update/{sermon_id}")
def update_sermon(
    sermon_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    sermon = db.query(Sermon).filter(Sermon.id == sermon_id).first()

    if not sermon:
        raise HTTPException(status_code=404, detail="Sermon not found")

    if sermon.author_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    if "title" in data:
        sermon.title = data["title"]

    if "content" in data:
        content = data["content"]
        if isinstance(content, dict):
            content = json.dumps(content)
        sermon.content = content

    sermon.updated_at = datetime.utcnow()

    db.commit()

    return {"message": "Updated successfully"}


# =========================
# 🔒 DELETE SERMON (OWNER ONLY)
# =========================
@router.delete("/sermon/{sermon_id}")
def delete_sermon(
    sermon_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    sermon = db.query(Sermon).filter(Sermon.id == sermon_id).first()

    if not sermon:
        raise HTTPException(status_code=404, detail="Sermon not found")

    if sermon.author_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(sermon)
    db.commit()

    return {"message": "Sermon deleted successfully"}