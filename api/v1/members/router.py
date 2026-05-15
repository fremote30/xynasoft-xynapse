from fastapi import APIRouter

router = APIRouter(prefix="/members", tags=["Members"])


@router.get("/")
def list_members():
    return {"members": []}


@router.post("/")
def create_member():
    return {"created": True}