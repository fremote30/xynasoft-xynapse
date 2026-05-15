from jose import jwt
from datetime import datetime, timedelta
import os
from api.core.config import SECRET_KEY, ALGORITHM
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", 12))

# 🔍 DEBUG CONFIG
print("🔐 [CREATE] SECRET_KEY:", SECRET_KEY)
print("🔐 [CREATE] ALGORITHM:", ALGORITHM)


def create_access_token(user_id: int):
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    payload = {
        "sub": str(user_id),   # 🔥 CRITICAL
        "exp": expire
    }

    print("🛠️ [CREATE] Creating token...")
    print("🛠️ [CREATE] Payload:", payload)
    print("🛠️ [CREATE] Using SECRET_KEY:", SECRET_KEY)

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    print("✅ [CREATE] Token generated:", token)

    return token