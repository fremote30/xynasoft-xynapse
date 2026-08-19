from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from datetime import datetime
import traceback

from api.db.database import SessionLocal
from api.models.user import User
from api.models.refresh_token import RefreshToken  # 🔥 NEW

from api.services.firebase_auth_service import (
    FirebaseConfigurationError,
    FirebasePhoneMissingError,
    FirebaseTokenError,
    verify_firebase_phone_token,
)

from api.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)

router = APIRouter(prefix="/auth", tags=["Auth"])


# =========================
# REQUEST SCHEMAS
# =========================
class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
   


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class PhoneLoginRequest(BaseModel):
    id_token: str


# =========================
# DB
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# PASSWORD VALIDATION 🔥
# =========================
def validate_password(password: str):
    if len(password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")


# =========================
# REGISTER (HARDENED)
# =========================
@router.post("/register")
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    try:
        validate_password(data.password)

        existing = db.query(User).filter(User.email == data.email).first()

        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")

        new_user = User(
            name=data.name,
            email=data.email,
            password=hash_password(data.password),
            role="member",
            is_verified=True
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {
            "message": "User created successfully"
        }

    except HTTPException:
        raise

    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


# =========================
# LOGIN (HARDENED)
# =========================
@router.post("/login")
def login(data: LoginRequest, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.email == data.email).first()

        if not user or not verify_password(data.password, user.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        # 🔥 SAVE REFRESH TOKEN
        db_token = RefreshToken(
            user_id=user.id,
            token=refresh_token
        )
        db.add(db_token)
        db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
                "pastor_status": user.pastor_status,
                "pastor_application_date": (
                    user.pastor_application_date.isoformat()
                    if user.pastor_application_date
                    else None
                )
            }
            
        }

    except HTTPException:
        raise

    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Internal Server Error")


# =========================
# PHONE LOGIN
# =========================
@router.post("/phone")
def phone_login(
    data: PhoneLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Exchange a Firebase-verified phone identity for a
    XynaFaith access/refresh-token session.

    This endpoint does not create new users yet. The verified
    phone number must already be linked to a XynaFaith account.
    """

    try:
        identity = verify_firebase_phone_token(
            data.id_token
        )

        phone = identity["phone"]

        user = (
            db.query(User)
            .filter(User.phone == phone)
            .first()
        )

        if not user:
            raise HTTPException(
                status_code=404,
                detail=(
                    "No XynaFaith account is linked "
                    "to this phone number"
                ),
            )

        # Firebase has just verified ownership of this number.
        if not user.phone_verified:
            user.phone_verified = True

        if user.auth_method == "email":
            user.auth_method = "email_phone"

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        db_token = RefreshToken(
            user_id=user.id,
            token=refresh_token,
        )

        db.add(db_token)
        db.commit()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "user": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "phone": user.phone,
                "role": user.role,
                "pastor_status": user.pastor_status,
                "pastor_application_date": (
                    user.pastor_application_date.isoformat()
                    if user.pastor_application_date
                    else None
                ),
            },
        }

    except HTTPException:
        raise

    except FirebaseConfigurationError:
        raise HTTPException(
            status_code=503,
            detail="Phone authentication is unavailable",
        )

    except (
        FirebaseTokenError,
        FirebasePhoneMissingError,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid phone authentication",
        )

    except Exception:
        db.rollback()
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="Internal Server Error",
        )


# =========================
# REFRESH TOKEN 🔥 NEW
# =========================
@router.post("/refresh")
def refresh(refresh_token: str, db: Session = Depends(get_db)):
    payload = decode_token(refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid refresh token")

    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token,
        RefreshToken.is_revoked == False
    ).first()

    if not db_token:
        raise HTTPException(401, "Token revoked")

    new_access = create_access_token(int(payload["sub"]))

    return {"access_token": new_access}


# =========================
# LOGOUT 🔥 NEW
# =========================
@router.post("/logout")
def logout(refresh_token: str, db: Session = Depends(get_db)):
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token
    ).first()

    if db_token:
        db_token.is_revoked = True
        db_token.revoked_at = datetime.utcnow()
        db.commit()

    return {"message": "Logged out"}


# =========================
# GET CURRENT USER (/me)
# =========================
@router.get("/me")
def get_me(
    authorization: str = Header(None),
    db: Session = Depends(get_db)
):
    try:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(401, "Missing or invalid token")

        token = authorization.split(" ")[1]

        payload = decode_token(token)

        if not payload or payload.get("type") != "access":
            raise HTTPException(401, "Invalid token")

        user_id = payload.get("sub")

        user = db.query(User).filter(User.id == int(user_id)).first()

        if not user:
            raise HTTPException(404, "User not found")

        return {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "pastor_status": user.pastor_status,
            "pastor_application_date": (
                user.pastor_application_date.isoformat()
                if user.pastor_application_date
                else None
            )
        }

    except HTTPException:
        raise

    except Exception:
        traceback.print_exc()
        raise HTTPException(status_code=401, detail="Invalid token")