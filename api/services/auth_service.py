from sqlalchemy.orm import Session
from api.models.user import User
from api.models.church import Church
from api.models.refresh_token import RefreshToken

from api.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token
)


# =========================
# 🔹 REGISTER USER
# =========================
def register_user(db: Session, data):
    """
    Creates a new church + user
    """

    # Create church
    church = Church(name=data.church_name)
    db.add(church)
    db.commit()
    db.refresh(church)

    # Create user
    user = User(
        name=data.name,
        email=data.email,
        password=hash_password(data.password),  # 🔐 ALWAYS HASH
        role=data.role,
        church_id=church.id,
        is_verified=True  # optional: auto-verify for now
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# =========================
# 🔹 LOGIN USER
# =========================
def login_user(db: Session, email: str, password: str):
    """
    Authenticates user and returns access + refresh tokens
    """

    user = db.query(User).filter(User.email == email).first()

    # ❌ user not found
    if not user:
        return None

    # ❌ wrong password
    if not verify_password(password, user.password):
        return None

    # 🔐 Create access token
    access_token = create_access_token({
        "user_id": user.id,
        "role": user.role
    })

    # 🔄 Create refresh token
    refresh_token = create_refresh_token({
        "user_id": user.id
    })

    # 💾 Store refresh token in DB
    token_record = RefreshToken(
        token=refresh_token,
        user_id=user.id
    )

    db.add(token_record)
    db.commit()

    # ✅ RETURN CLEAN RESPONSE (IMPORTANT FOR FRONTEND)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }


# =========================
# 🔹 GET CURRENT USER
# =========================
def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()