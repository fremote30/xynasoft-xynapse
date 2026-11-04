from fastapi import APIRouter
from uuid import uuid4

router = APIRouter(prefix="/faith/collab", tags=["Faith Collaboration"])

# simple in-memory store for demo
SERMONS = {}


@router.post("/create")
def create_collab_sermon():

    sermon_id = str(uuid4())

    SERMONS[sermon_id] = {
        "title": "Untitled Sermon",
        "content": "",
        "collaborators": []
    }

    return {
        "sermon_id": sermon_id,
        "message": "Collaboration sermon created"
    }


@router.get("/{sermon_id}")
def get_sermon(sermon_id: str):

    sermon = SERMONS.get(sermon_id)

    if not sermon:
        return {"error": "sermon not found"}

    return sermon


@router.post("/{sermon_id}/update")
def update_sermon(sermon_id: str, payload: dict):

    sermon = SERMONS.get(sermon_id)

    if not sermon:
        return {"error": "sermon not found"}

    sermon["content"] = payload.get("content", sermon["content"])
    sermon["title"] = payload.get("title", sermon["title"])

    return {"status": "updated"}