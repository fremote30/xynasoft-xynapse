from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.models.push_device_token import PushDeviceToken
from api.models.user import User


router = APIRouter(
    prefix="/devices",
    tags=["Push Devices"],
)


class PushTokenRequest(BaseModel):
    token: str
    platform: Literal["android", "ios"]


@router.post("/push-token")
def register_push_token(
    payload: PushTokenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    token = payload.token.strip()

    if not token:
        return {
            "status": "ignored",
            "message": "Empty push token",
        }

    existing = (
        db.query(PushDeviceToken)
        .filter(PushDeviceToken.token == token)
        .first()
    )

    if existing:
        existing.user_id = current_user.id
        existing.platform = payload.platform
        existing.is_active = True
        existing.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(existing)

        return {
            "status": "updated",
            "device_id": existing.id,
        }

    device = PushDeviceToken(
        user_id=current_user.id,
        token=token,
        platform=payload.platform,
        is_active=True,
    )

    db.add(device)
    db.commit()
    db.refresh(device)

    return {
        "status": "registered",
        "device_id": device.id,
    }


@router.delete("/push-token")
def remove_push_token(
    payload: PushTokenRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device = (
        db.query(PushDeviceToken)
        .filter(
            PushDeviceToken.token == payload.token,
            PushDeviceToken.user_id == current_user.id,
        )
        .first()
    )

    if not device:
        return {
            "status": "not_found",
        }

    device.is_active = False
    device.updated_at = datetime.utcnow()

    db.commit()

    return {
        "status": "deactivated",
    }
