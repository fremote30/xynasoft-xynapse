import os

SECRET_KEY = os.getenv("SECRET_KEY") or "fallback-secret-key"
ALGORITHM = os.getenv("ALGORITHM", "HS256")

print("🔐 CONFIG LOADED")
print("🔐 SECRET_KEY:", SECRET_KEY)
print("🔐 ALGORITHM:", ALGORITHM)

# =========================================
# XYNASSIST INTEGRATION
# =========================================

XYNASSIST_ENABLED = (
    os.getenv("XYNASSIST_ENABLED", "false")
    .strip()
    .lower()
    in {"1", "true", "yes", "on"}
)

XYNASSIST_BASE_URL = (
    os.getenv(
        "XYNASSIST_BASE_URL",
        "http://localhost:8001",
    )
    .strip()
    .rstrip("/")
)

XYNASSIST_TIMEOUT_SECONDS = float(
    os.getenv(
        "XYNASSIST_TIMEOUT_SECONDS",
        "30",
    )
)
