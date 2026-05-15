from fastapi import APIRouter

router = APIRouter(prefix="/pastors", tags=["Pastors"])


@router.get("/")
def list_pastors():
    return {"pastors": []}


@router.get("/{pastor_id}")
def pastor_profile(pastor_id: int):
    return {"pastor_id": pastor_id}


@router.post("/")
def create_pastor():
    return {"created": True}