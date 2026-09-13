from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    text,
)

from api.db.database import Base


class AIUsageReservation(Base):
    """
    Idempotent reservation for one metered AI request.

    The unique request_id prevents retries from reserving the same
    allowance more than once.
    """

    __tablename__ = "ai_usage_reservations"

    __table_args__ = (
        CheckConstraint(
            "units > 0",
            name="ck_ai_usage_reservations_positive_units",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
    )

    request_id = Column(
        String(128),
        nullable=False,
        unique=True,
        index=True,
    )

    bucket_id = Column(
        Integer,
        ForeignKey(
            "usage_buckets.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    church_id = Column(
        Integer,
        ForeignKey(
            "churches.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    subscription_id = Column(
        Integer,
        ForeignKey(
            "subscriptions.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    entitlement_key = Column(
        String(120),
        nullable=False,
        index=True,
    )

    metric = Column(
        String(64),
        nullable=False,
        index=True,
    )

    units = Column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    status = Column(
        String(32),
        nullable=False,
        default="reserved",
        server_default="reserved",
        index=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
        onupdate=datetime.utcnow,
    )

    completed_at = Column(
        DateTime,
        nullable=True,
    )

    released_at = Column(
        DateTime,
        nullable=True,
    )
