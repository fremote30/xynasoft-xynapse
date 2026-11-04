"""
Transaction boundary for metered Xyniva conversation turns.

Entitlement resolution and atomic quota accounting live in
xyniva_usage_service / ai_usage_metering. This module owns the
database commit/rollback semantics required around an expensive
external XynAssist call.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from api.models.user import User
from api.services.xyniva_usage_service import (
    complete_xyniva_usage,
    release_xyniva_usage,
    reserve_xyniva_usage,
)


XYNIVA_CHAT_ENTITLEMENT = "xyniva.chat"
XYNIVA_CHAT_METRIC = "conversation_turn"


def reserve_conversation_turn(
    db: Session,
    *,
    user: User,
    request_id: str,
    church_id: Optional[int] = None,
    now: Optional[datetime] = None,
):
    """
    Reserve one Xyniva conversation turn and durably commit it.

    The commit occurs before the external XynAssist request so another
    concurrent request observes the reservation and cannot overspend
    the same quota.
    """
    try:
        reservation = reserve_xyniva_usage(
            db,
            user=user,
            request_id=request_id,
            entitlement_key=XYNIVA_CHAT_ENTITLEMENT,
            metric=XYNIVA_CHAT_METRIC,
            units=1,
            church_id=church_id,
            now=now,
        )
        db.commit()
        return reservation
    except Exception:
        db.rollback()
        raise


def consume_conversation_turn(
    db: Session,
    *,
    request_id: str,
    now: Optional[datetime] = None,
):
    """
    Convert a durable reservation into consumed usage.
    """
    try:
        reservation = complete_xyniva_usage(
            db,
            request_id=request_id,
            now=now,
        )
        db.commit()
        return reservation
    except Exception:
        db.rollback()
        raise


def release_conversation_turn(
    db: Session,
    *,
    request_id: str,
    now: Optional[datetime] = None,
):
    """
    Return reserved quota when XynAssist fails before producing a
    successful turn.
    """
    try:
        reservation = release_xyniva_usage(
            db,
            request_id=request_id,
            now=now,
        )
        db.commit()
        return reservation
    except Exception:
        db.rollback()
        raise
