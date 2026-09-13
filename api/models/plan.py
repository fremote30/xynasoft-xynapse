from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from api.db.database import Base


class Plan(Base):
    """
    XynaFaith V2 product plan.

    Plan codes are internal product identifiers and are intentionally
    independent from any payment-provider product or price ID.
    """

    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)

    code = Column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    name = Column(
        String(120),
        nullable=False,
    )

    access_profile = Column(
        String(64),
        nullable=False,
    )

    # individual | church
    owner_type = Column(
        String(32),
        nullable=False,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
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

    entitlements = relationship(
        "PlanEntitlement",
        back_populates="plan",
        cascade="all, delete-orphan",
    )

    subscriptions = relationship(
        "Subscription",
        back_populates="plan",
    )
