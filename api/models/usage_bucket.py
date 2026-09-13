from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)

from api.db.database import Base


class UsageBucket(Base):
    """
    Atomic usage counter for one entitlement/metric/time period.

    A bucket belongs to exactly one quota owner:
    either an individual user or a Church Space.

    reserved_units are held by AI requests currently in flight.
    consumed_units represent successfully completed metered work.
    """

    __tablename__ = "usage_buckets"

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
            name="ck_usage_buckets_exactly_one_owner",
        ),
        CheckConstraint(
            "consumed_units >= 0",
            name="ck_usage_buckets_consumed_nonnegative",
        ),
        CheckConstraint(
            "reserved_units >= 0",
            name="ck_usage_buckets_reserved_nonnegative",
        ),
        CheckConstraint(
            "allowance_units >= 0",
            name="ck_usage_buckets_allowance_nonnegative",
        ),
        CheckConstraint(
            "period_end > period_start",
            name="ck_usage_buckets_valid_period",
        ),
        Index(
            "uq_usage_buckets_user_period",
            "user_id",
            "entitlement_key",
            "metric",
            "period_start",
            unique=True,
            postgresql_where=text("user_id IS NOT NULL"),
            sqlite_where=text("user_id IS NOT NULL"),
        ),
        Index(
            "uq_usage_buckets_church_period",
            "church_id",
            "entitlement_key",
            "metric",
            "period_start",
            unique=True,
            postgresql_where=text("church_id IS NOT NULL"),
            sqlite_where=text("church_id IS NOT NULL"),
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    church_id = Column(
        Integer,
        ForeignKey(
            "churches.id",
            ondelete="CASCADE",
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

    period_start = Column(
        DateTime,
        nullable=False,
        index=True,
    )

    period_end = Column(
        DateTime,
        nullable=False,
    )

    allowance_units = Column(
        Integer,
        nullable=False,
    )

    consumed_units = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    reserved_units = Column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
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
