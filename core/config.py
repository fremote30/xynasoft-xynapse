import os

# =========================
# 🔐 CORE CONFIG (FIXED)
# =========================
SECRET_KEY = os.getenv("SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "SECRET_KEY environment variable is required"
    )
ALGORITHM = os.getenv("ALGORITHM", "HS256")

print("🔐 CONFIG LOADED")
print("🔐 ALGORITHM:", ALGORITHM)