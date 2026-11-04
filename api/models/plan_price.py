"""
Provider-agnostic pricing model for XynaFaith V2 commercial plans.

PlanPrice describes what XynaFaith charges for a plan in a commercial
market. It deliberately contains no Stripe or other payment-provider IDs.

Money is stored in minor currency units (for example cents or pesewas)
rather than floating-point values.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.orm import relationship

from api.db.database import Base


BILLING_INTERVAL_MONTHLY = "monthly"
BILLING_INTERVAL_ANNUAL = "annual"

BILLING_INTERVALS = frozenset(
    {
        BILLING_INTERVAL_MONTHLY,
        BILLING_INTERVAL_ANNUAL,
    }
)


class PlanPrice(Base):
    """
    Internal commercial price for one XynaFaith plan.

    A plan may have multiple prices across markets, currencies, billing
    intervals, and effective periods.

    Provider-specific product/price identifiers belong in a separate
    integration layer and are intentionally absent here.
    """

    __tablename__ = "plan_prices"

    __table_args__ = (
        CheckConstraint(
            "amount_minor >= 0",
            name="ck_plan_prices_amount_nonnegative",
        ),
        CheckConstraint(
            "billing_interval IN ('monthly', 'annual')",
            name="ck_plan_prices_billing_interval",
        ),
        CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="ck_plan_prices_valid_effective_period",
        ),
        Index(
            "ix_plan_prices_plan_market_active",
            "plan_id",
            "market_code",
            "is_active",
        ),
        Index(
            "ix_plan_prices_market_currency",
            "market_code",
            "currency",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
    )

    plan_id = Column(
        Integer,
        ForeignKey(
            "plans.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # Examples: US, GH, GLOBAL.
    market_code = Column(
        String(32),
        nullable=False,
        index=True,
    )

    # ISO 4217-style currency code, e.g. USD or GHS.
    currency = Column(
        String(3),
        nullable=False,
    )

    billing_interval = Column(
        String(16),
        nullable=False,
    )

    amount_minor = Column(
        Integer,
        nullable=False,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    effective_from = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
    )

    effective_until = Column(
        DateTime,
        nullable=True,
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

    plan = relationship(
        "Plan",
        back_populates="prices",
    )
