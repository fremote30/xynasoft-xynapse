# =====================================
# XynaFAITH COMMUNITY / NETWORK ROUTES
# =====================================

from typing import Optional

from fastapi import (
    APIRouter,
    Depends,
    Header
)

from sqlalchemy.orm import Session

from api.core.security import decode_token
from api.db.database import get_db
from api.models.user import User
from api.services.platform_service import (
    PlatformService
)


router = APIRouter(
    prefix="/network",
    tags=["Community"]
)


# =====================================
# OPTIONAL AUTHENTICATION
# =====================================
def get_optional_current_user(
    authorization: Optional[str],
    db: Session
) -> Optional[User]:

    if (
        not authorization
        or not authorization.startswith(
            "Bearer "
        )
    ):
        return None

    token = authorization.split(
        " ",
        1
    )[1]

    payload = decode_token(token)

    if not payload:
        return None

    user_id = payload.get("sub")

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        return None

    return (
        db.query(User)
        .filter(
            User.id == user_id
        )
        .first()
    )


# =====================================
# NETWORK OVERVIEW
# =====================================
@router.get("/overview")
def get_network_overview(
    authorization: Optional[str] = Header(
        None
    ),
    db: Session = Depends(get_db)
):

    current_user = get_optional_current_user(
        authorization,
        db
    )

    return (
        PlatformService
        .get_network_overview(
            db,
            current_user
        )
    )