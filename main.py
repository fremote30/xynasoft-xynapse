import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from api.routes.follow_routes import router as follow_router
# ================================
# 🔥 IMPORT ALL MODELS (CRITICAL)
# ================================
from api.models.user import User
from api.models.church import Church
from api.models.refresh_token import RefreshToken
from api.models.sermon import Sermon
from api.models.pastor_member import PastorMember  # 🔥 NEW

from api.models import shared_sermon
from api.models import sermon_comment
from api.routes.dashboard_routes import router as dashboard_router

# ================================
# ROUTES
# ================================
from api.routes.comment_routes import router as comment_router
from api.db.database import Base, engine
from api.routes import auth
from api.routes.collaboration_routes import router as collab_router

# 🔥 Sermon AI (generation)
from api.v1.faith.sermon import router as sermon_router

# 🔥 Sermon CRUD
from api.routes.sermon_routes import router as sermon_crud_router

# 🔥 Upload Sermon
from api.routes import upload
# Shared sermon
from api.models.shared_sermon import SharedSermon
from api.routes.users import router as users_router
from api.routes.pastors import router as pastors_router
from api.models.pastor_profile import PastorProfile
from api.routes.pastor_profile import (router as pastor_profile_router)

# ================================
# 🚀 INIT APP
# ================================
app = FastAPI(title="XynaFaith API")


# ================================
# 🗄️ DATABASE
# ================================
print("🚀 Starting API...")
print("📦 Connecting to DB...")

# 🔥 THIS NOW INCLUDES ALL MODELS
Base.metadata.create_all(bind=engine)

print("✅ Database ready")


# ================================
# 🌐 CORS (ALLOW FRONTEND)
# ================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("✅ CORS enabled")


# ================================
# 🔗 ROUTES
# ================================

# ✅ Auth
app.include_router(auth.router)
print("✅ Auth routes loaded")

# ✅ Sermon AI
app.include_router(sermon_router, prefix="/api/v1")
print("✅ Sermon AI routes loaded")

# ✅ Sermon CRUD
app.include_router(sermon_crud_router, prefix="/api")
print("✅ Sermon CRUD routes loaded")

# ✅ Upload
app.include_router(upload.router, prefix="/sermon")
print("✅ Sermon Upload routes loaded")

# ✅ Collaboration
app.include_router(collab_router, prefix="/api")

# ✅ Comments
app.include_router(comment_router, prefix="/api")
#Follower
app.include_router(follow_router)

#Dashboard
app.include_router(dashboard_router, prefix="/api/v1")

#User
app.include_router(users_router, prefix="/api/v1")
#Follow pastor
app.include_router(pastors_router,prefix="/api/v1")

app.include_router(pastor_profile_router,prefix="/api/v1")
# ================================
# 📁 FRONTEND (SPA)
# ================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAITH_DIR = os.path.join(BASE_DIR, "ui-faith")

print("📁 BASE_DIR:", BASE_DIR)
print("📁 UI DIR:", FAITH_DIR)

if os.path.exists(FAITH_DIR):

    app.mount("/faith", StaticFiles(directory=FAITH_DIR), name="faith")
    print("✅ Frontend mounted at /faith")

else:
    print("❌ ERROR: ui-faith folder not found")
    print("📁 Available:", os.listdir(BASE_DIR))


# ================================
# 🏠 ROOT → LOAD SPA
# ================================
@app.get("/")
def root():
    layout_path = os.path.join(FAITH_DIR, "layout.html")

    if os.path.exists(layout_path):
        return FileResponse(layout_path)

    return {
        "error": "layout.html not found",
        "checked_path": layout_path,
        "files_here": os.listdir(FAITH_DIR) if os.path.exists(FAITH_DIR) else []
    }


# ================================
# 🔁 OPTIONAL ENTRY
# ================================
@app.get("/app")
def app_entry():
    layout_path = os.path.join(FAITH_DIR, "layout.html")

    if os.path.exists(layout_path):
        return FileResponse(layout_path)

    return {"error": "layout.html missing"}


# ================================
# ❤️ HEALTH CHECK
# ================================
@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "XynaFaith API",
        "ai": "enabled",
        "features": [
            "sermon_generation",
            "sermon_save",
            "sermon_history",
            "sermon_edit",
            "sermon_upload"
        ]
    }