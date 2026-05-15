import os

# =========================
# 🔐 CORE CONFIG (FIXED)
# =========================
SECRET_KEY = os.getenv("SECRET_KEY") or "fallback-secret-key"
ALGORITHM = os.getenv("ALGORITHM", "HS256")

print("🔐 CONFIG LOADED")
print("🔐 SECRET_KEY:", SECRET_KEY)
print("🔐 ALGORITHM:", ALGORITHM)