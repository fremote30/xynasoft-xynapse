from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from uuid import uuid4

from api.db.database import get_db
from api.models.pastor import Pastor

router = APIRouter(prefix="/auth", tags=["Faith Auth"])

# temporary session store
SESSIONS = {}


# -----------------------------
# REGISTER
# -----------------------------
@router.post("/register")
def register(payload: dict, db: Session = Depends(get_db)):

    pastor = Pastor(
        name=payload.get("name"),
        email=payload.get("email"),
        password=payload.get("password"),
        church=payload.get("church"),
        country=payload.get("country"),
        denomination=payload.get("denomination")
    )

    db.add(pastor)
    db.commit()
    db.refresh(pastor)

    return {
        "status": "registered",
        "pastor_id": pastor.pastor_id
    }


# -----------------------------
# LOGIN
# -----------------------------
@router.post("/login")
def login(payload: dict, db: Session = Depends(get_db)):

    email = payload.get("email")
    password = payload.get("password")

    pastor = db.query(Pastor).filter(Pastor.email == email).first()

    if not pastor or pastor.password != password:
        return {"error": "invalid credentials"}

    token = str(uuid4())

    SESSIONS[token] = pastor.pastor_id

    return {
        "token": token,
        "pastor_id": pastor.pastor_id,
        "name": pastor.name
    }


# -----------------------------
# PROFILE
# -----------------------------
@router.get("/me/{token}")
def profile(token: str, db: Session = Depends(get_db)):

    pastor_id = SESSIONS.get(token)

    if not pastor_id:
        return {"error": "invalid session"}

    pastor = db.query(Pastor).filter(Pastor.pastor_id == pastor_id).first()

    return {
        "pastor_id": pastor.pastor_id,
        "name": pastor.name,
        "email": pastor.email,
        "church": pastor.church,
        "country": pastor.country,
        "denomination": pastor.denomination
    }