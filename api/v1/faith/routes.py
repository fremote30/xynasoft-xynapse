from fastapi import APIRouter

from api.v1.faith.auth.router import router as auth_router

router = APIRouter(prefix="/faith", tags=["Faith"])

# include auth routes
router.include_router(auth_router)


# -----------------------------
# STATUS ENDPOINT
# -----------------------------
@router.get("/status")
def faith_status():
    return {
        "module": "XynaFaith",
        "status": "running"
    }