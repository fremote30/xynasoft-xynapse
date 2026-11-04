from fastapi import APIRouter

# Existing module
from api.v1.faith.routes import router as faith_router

# 🔥 NEW — auth routes
from api.routes.auth import router as auth_router

api_router = APIRouter()

# =========================
# 🔹 AUTH ROUTES
# =========================
api_router.include_router(auth_router, tags=["Auth"])

# =========================
# 🔹 FAITH MODULE
# =========================
api_router.include_router(faith_router, prefix="/faith", tags=["Faith"])