from jose import jwt, JWTError
from datetime import datetime, timedelta
import os

from fastapi import Header, HTTPException, Depends
from sqlalchemy.orm import Session

from api.db.database import get_db
from api.models.user import User
from api.core.config import SECRET_KEY, ALGORITHM

# =========================
# 🔐 CONFIG
# =========================
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("ACCESS_TOKEN_EXPIRE_HOURS", 12))

print("🔐 SECRET_KEY (DECODE SIDE):", SECRET_KEY)
print("🔐 ALGORITHM:", ALGORITHM)


# =========================
# 🔑 CREATE TOKEN
# =========================
def create_access_token(user_id: int):
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    payload = {
        "sub": str(user_id),
        "exp": expire
    }

    print("🛠️ CREATING TOKEN WITH SECRET:", SECRET_KEY)
    print("🛠️ PAYLOAD:", payload)

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

    print("✅ TOKEN CREATED:", token)
    return token


# =========================
# 🔓 DECODE TOKEN
# =========================
def decode_token(token: str):
    try:
        print("📥 DECODING TOKEN:", token)
        print("🔐 USING SECRET:", SECRET_KEY)

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        print("🔓 TOKEN DECODED SUCCESS:", payload)
        return payload

    except JWTError as e:
        print("❌ JWT DECODE ERROR:", str(e))
        return None


# =========================
# 👤 GET CURRENT USER
# =========================
def get_current_user(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    print("📡 AUTH HEADER RECEIVED:", authorization)

    if not authorization:
        print("❌ No Authorization header")
        raise HTTPException(status_code=401, detail="Missing token")

    try:
        if not authorization.startswith("Bearer "):
            print("❌ Invalid Authorization format:", authorization)
            raise HTTPException(status_code=401, detail="Invalid auth header")

        token = authorization.replace("Bearer ", "").strip()

        print("📥 TOKEN EXTRACTED:", token)

        # =========================
        # 🔓 DECODE
        # =========================
        payload = decode_token(token)

        if not payload:
            print("❌ Payload is None → invalid token")
            raise HTTPException(status_code=401, detail="Invalid token")

        # =========================
        # 🔥 EXTRACT USER ID
        # =========================
        user_id = payload.get("sub")

        print("🧾 PAYLOAD CONTENT:", payload)

        if not user_id:
            print("❌ Missing 'sub' in payload")
            raise HTTPException(status_code=401, detail="Invalid token payload")

        print("👤 USER ID FROM TOKEN:", user_id)

        # =========================
        # 🔎 FETCH USER
        # =========================
        user = db.query(User).filter(User.id == int(user_id)).first()

        if not user:
            print("❌ User NOT found in DB for ID:", user_id)
            raise HTTPException(status_code=404, detail="User not found")

        print("✅ AUTH SUCCESS → USER:", user.email)

        return user

    except HTTPException:
        raise

    except Exception as e:
        print("❌ AUTH EXCEPTION:", str(e))
        raise HTTPException(status_code=401, detail="Invalid token")