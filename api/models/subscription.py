from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from api.db.database import Base


class Subscription(Base):
    """
    XynaFaith V2 subscription.

    A subscription belongs to exactly one owner:
    either an individual user or a Church Space.

    Payment-provider identity is deliberately not required here.
    """

    __tablename__ = "subscriptions"

    __table_args__ = (
        CheckConstraint(
            """
            (
                user_id IS NOT NULL
                AND church_id IS NULL
            )
            OR
            (
                user_id IS NULL
                AND church_id IS NOT NULL
            )
            """,
            name="ck_subscriptions_exactly_one_owner",
        ),
    )

    id = Column(Integer, primary_key=True)

    plan_id = Column(
        Integer,
        ForeignKey("plans.id"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    church_id = Column(
        Integer,
        ForeignKey("churches.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # active | trialing | canceled | expired | suspended
    status = Column(
        String(32),
        nullable=False,
        default="active",
    )

    starts_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    current_period_start = Column(
        DateTime,
        nullable=True,
    )

    current_period_end = Column(
        DateTime,
        nullable=True,
    )

    canceled_at = Column(
        DateTime,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    plan = relationship(
        "Plan",
        back_populates="subscriptions",
    )
