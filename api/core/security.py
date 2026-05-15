from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
import os

# =========================
# 🔐 CONFIG (PRODUCTION READY)
# =========================
SECRET_KEY = os.getenv("SECRET_KEY") or "CHANGE_THIS_IN_PRODUCTION"
ALGORITHM = os.getenv("ALGORITHM", "HS256")

ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)  # 🔥 1 hour (NOT 1 day)
)

REFRESH_TOKEN_EXPIRE_DAYS = int(
    os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7)
)


# =========================
# 🔐 PASSWORD HASHING
# =========================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# =========================
# 🔐 ACCESS TOKEN
# =========================
def create_access_token(user_id: int):
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload = {
        "sub": str(user_id),   # ✅ REQUIRED
        "type": "access",      # 🔥 NEW (important)
        "exp": expire
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# =========================
# 🔄 REFRESH TOKEN
# =========================
def create_refresh_token(user_id: int):
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    payload = {
        "sub": str(user_id),
        "type": "refresh",     # 🔥 CRITICAL DIFFERENCE
        "exp": expire
    }

    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# =========================
# 🔓 DECODE TOKEN
# =========================
def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None