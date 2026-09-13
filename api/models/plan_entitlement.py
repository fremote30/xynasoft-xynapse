from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from api.db.database import Base


class PlanEntitlement(Base):
    """
    Feature entitlement assigned to a product plan.

    usage_limit=None means that the entitlement itself does not impose
    a numeric cap. Limits are product policy, not payment-provider data.
    """

    __tablename__ = "plan_entitlements"

    __table_args__ = (
        UniqueConstraint(
            "plan_id",
            "entitlement_key",
            name="uq_plan_entitlements_plan_key",
        ),
    )

    id = Column(Integer, primary_key=True)

    plan_id = Column(
        Integer,
        ForeignKey("plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    entitlement_key = Column(
        String(120),
        nullable=False,
    )

    enabled = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    usage_limit = Column(
        Integer,
        nullable=True,
    )

    # monthly | daily | none
    usage_period = Column(
        String(32),
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    plan = relationship(
        "Plan",
        back_populates="entitlements",
    )
