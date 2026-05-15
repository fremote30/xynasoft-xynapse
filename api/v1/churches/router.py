from fastapi import APIRouter

router = APIRouter(prefix="/churches", tags=["Churches"])


@router.get("/")
def list_churches():
    return {"churches": []}


@router.get("/{church_id}")
def church_page(church_id: int):
    return {"church_id": church_id}