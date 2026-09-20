"""
Transaction boundary for metered XynaFaith ministry AI skills.

Commercial access remains owned by XynaFaith. XynAssist executes the
provider-independent ministry intelligence after XynaFaith has durably
reserved the appropriate entitlement quota.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from api.core.entitlements import (
    ENTITLEMENT_BIBLICAL_RESEARCH,
    ENTITLEMENT_SERMON_STUDIO,
)
from api.models.user import User
from api.services.xyniva_usage_service import (
    complete_xyniva_usage,
    release_xyniva_usage,
    reserve_xyniva_usage,
)


MINISTRY_SKILL_ACCESS = {
    "sermon.generate": (
        ENTITLEMENT_SERMON_STUDIO,
        "sermon_generation",
    ),
    "sermon.refine": (
        ENTITLEMENT_SERMON_STUDIO,
        "sermon_refinement",
    ),
    "biblical.research": (
        ENTITLEMENT_BIBLICAL_RESEARCH,
        "biblical_research",
    ),
}


class UnknownMinistrySkill(ValueError):
    """The product does not expose the requested ministry skill."""


def ministry_skill_access(
    skill: str,
) -> tuple[str, str]:
    try:
        return MINISTRY_SKILL_ACCESS[skill]
    except KeyError as exc:
        raise UnknownMinistrySkill(
            f"Unsupported ministry skill: {skill}"
        ) from exc


def reserve_ministry_skill(
    db: Session,
    *,
    user: User,
    request_id: str,
    skill: str,
    church_id: Optional[int] = None,
    now: Optional[datetime] = None,
):
    """
    Reserve and durably commit one ministry AI unit before XynAssist.

    Entitlement selection is server-controlled from the skill name.
    The caller cannot choose a cheaper or unrelated entitlement.
    """

    entitlement_key, metric = ministry_skill_access(
        skill
    )

    try:
        reservation = reserve_xyniva_usage(
            db,
            user=user,
            request_id=request_id,
            entitlement_key=entitlement_key,
            metric=metric,
            units=1,
            church_id=church_id,
            now=now,
        )
        db.commit()
        return reservation
    except Exception:
        db.rollback()
        raise


def consume_ministry_skill(
    db: Session,
    *,
    request_id: str,
    now: Optional[datetime] = None,
):
    """Consume one successfully completed ministry reservation."""

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


def release_ministry_skill(
    db: Session,
    *,
    request_id: str,
    now: Optional[datetime] = None,
):
    """
    Release ministry quota after failure before successful AI output.
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
