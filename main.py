import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# ================================
# 🔥 IMPORT ALL MODELS (CRITICAL)
# ================================
from api.models.user import User
from api.models.church import Church
from api.models.refresh_token import RefreshToken
from api.models.sermon import Sermon
from api.models.pastor_member import PastorMember
from api.models.shared_sermon import SharedSermon
from api.models.pastor_profile import PastorProfile

from api.models import shared_sermon
from api.models import sermon_comment

# ================================
# DATABASE
# ================================
from api.db.database import Base, engine

# ================================
# ROUTES
# ================================

# ✅ Auth
from api.routes import auth

# ✅ Dashboard
from api.routes.dashboard_routes import router as dashboard_router

# ✅ Comments
from api.routes.comment_routes import router as comment_router

# ✅ Collaboration
from api.routes.collaboration_routes import router as collab_router

# ✅ Followers
from api.routes.follow_routes import router as follow_router

# ✅ Users
from api.routes.users import router as users_router

# ✅ Pastors
from api.routes.pastors import router as pastors_router

# ✅ Pastor Profile
from api.routes.pastor_profile import (
    router as pastor_profile_router
)

# ✅ Sermon CRUD
from api.routes.sermon_routes import (
    router as sermon_crud_router
)

# ✅ Upload Sermon
from api.routes import upload

# =========================================
# ✅ NEW XYNAFAITH AI ROUTES (STEP 1D)
# =========================================
from api.routes.faith import (
    router as faith_router
)

# =========================================
# For Prayer Wall
# =========================================
from api.models.prayer import Prayer

# =========================================
# For Prayer Wall
# =========================================

from api.routes.prayer_routes import (
    router as prayer_router
)

# ================================
# 🚀 INIT APP
# ================================
app = FastAPI(title="XynaFaith API")

# ================================
# 🗄️ DATABASE
# ================================
print("🚀 Starting API...")
print("📦 Connecting to DB...")

# 🔥 CREATE ALL TABLES
# Base.metadata.create_all(bind=engine)

print("✅ Database ready")

# ================================
# 🌐 CORS
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

# =====================================
# AUTH
# =====================================
app.include_router(auth.router)
print("✅ Auth routes loaded")

# =====================================
# XYNAFAITH AI (NEW)
# =====================================
app.include_router(
    faith_router,
    prefix="/api/v1/faith",
    tags=["Faith"]
)

print("✅ XynaFaith AI routes loaded")

# =====================================
# SERMON CRUD
# =====================================
app.include_router(
    sermon_crud_router,
    prefix="/api"
)

print("✅ Sermon CRUD routes loaded")

# =====================================
# SERMON UPLOAD
# =====================================
app.include_router(
    upload.router,
    prefix="/sermon"
)

print("✅ Sermon Upload routes loaded")

# =====================================
# COLLABORATION
# =====================================
app.include_router(
    collab_router,
    prefix="/api"
)

print("✅ Collaboration routes loaded")

# =====================================
# COMMENTS
# =====================================
app.include_router(
    comment_router,
    prefix="/api"
)

print("✅ Comment routes loaded")

# =====================================
# FOLLOW SYSTEM
# =====================================
app.include_router(follow_router)

print("✅ Follow routes loaded")

# =====================================
# DASHBOARD
# =====================================
app.include_router(
    dashboard_router,
    prefix="/api/v1"
)

print("✅ Dashboard routes loaded")

# =====================================
# USERS
# =====================================
app.include_router(
    users_router,
    prefix="/api/v1"
)

print("✅ User routes loaded")

# =====================================
# PASTORS
# =====================================
app.include_router(
    pastors_router,
    prefix="/api/v1"
)

# =====================================
# For Prayer Wall
# =====================================
app.include_router(
    prayer_router,
    prefix="/api/v1"
)
print("✅ Prayer routes loaded")

# =====================================
# PASTOR PROFILE
# =====================================
app.include_router(
    pastor_profile_router,
    prefix="/api/v1"
)

print("✅ Pastor profile routes loaded")

# =====================================
# PASTOR PROFILE IMAGE UPLOADS
# =====================================
app.include_router(
    upload.router,
    prefix="/sermon"
)

# ================================
# 📁 FRONTEND (SPA)
# ================================
BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

FAITH_DIR = os.path.join(
    BASE_DIR,
    "ui-faith"
)

UPLOADS_DIR = os.path.join(
    BASE_DIR,
    "uploads"
)

os.makedirs(
    UPLOADS_DIR,
    exist_ok=True
)

app.mount(
    "/uploads",
    StaticFiles(directory=UPLOADS_DIR),
    name="uploads"
)

print("✅ Uploads mounted at /uploads")

print("📁 BASE_DIR:", BASE_DIR)
print("📁 UI DIR:", FAITH_DIR)

if os.path.exists(FAITH_DIR):

    app.mount(
        "/faith",
        StaticFiles(directory=FAITH_DIR),
        name="faith"
    )

    print("✅ Frontend mounted at /faith")

else:

    print("❌ ERROR: ui-faith folder not found")
    print("📁 Available:", os.listdir(BASE_DIR))

# ================================
# 🏠 ROOT → LOAD SPA
# ================================
@app.get("/")
def root():

    layout_path = os.path.join(
        FAITH_DIR,
        "layout.html"
    )

    if os.path.exists(layout_path):

        return FileResponse(layout_path)

    return {
        "error": "layout.html not found",
        "checked_path": layout_path,
        "files_here": (
            os.listdir(FAITH_DIR)
            if os.path.exists(FAITH_DIR)
            else []
        )
    }

# ================================
# 🔁 OPTIONAL ENTRY
# ================================
@app.get("/app")
def app_entry():

    layout_path = os.path.join(
        FAITH_DIR,
        "layout.html"
    )

    if os.path.exists(layout_path):

        return FileResponse(layout_path)

    return {
        "error": "layout.html missing"
    }

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
            "sermon_upload",
            "structured_sermon_json",
            "xynafaith_ai",
            "focus_mode",
            "mobile_sermon_studio"
        ]
    }