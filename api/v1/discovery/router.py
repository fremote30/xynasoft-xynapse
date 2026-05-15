from fastapi import APIRouter

router = APIRouter(prefix="/discovery", tags=["Discovery"])


@router.get("/pastors")
def discover_pastors():
    return {"results": []}