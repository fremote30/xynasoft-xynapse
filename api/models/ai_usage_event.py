from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from api.db.database import Base


class AIUsageEvent(Base):
    """
    Immutable XynaFaith/Xyniva AI usage event.

    request_id provides idempotency so retries do not accidentally
    consume a user's allowance multiple times.
    """

    __tablename__ = "ai_usage_events"

    id = Column(Integer, primary_key=True)

    request_id = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    church_id = Column(
        Integer,
        ForeignKey("churches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    subscription_id = Column(
        Integer,
        ForeignKey("subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    entitlement_key = Column(
        String(120),
        nullable=False,
        index=True,
    )

    # Examples:
    # xyniva_turn
    # sermon_generation
    # biblical_research
    # devotional_generation
    metric = Column(
        String(64),
        nullable=False,
        index=True,
    )

    units = Column(
        Integer,
        nullable=False,
        default=1,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
    )
