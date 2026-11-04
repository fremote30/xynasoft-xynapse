"""
Versioned provider/model token cost rates for XynAssist.

Rates describe the cost of provider executions, not customer pricing.

Historical rows are preserved so an AIExecution can always be evaluated
against the provider/model rate that was effective when it occurred.

Amounts are stored as integer micro-US-dollars per one million tokens:
    1 USD = 1_000_000 micro-USD.

No floating point money is stored.
"""

from __future__ import annotations

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Index,
    Integer,
    String,
    func,
)

from xynassist_service.db.database import Base


class AICostRate(Base):
    __tablename__ = "xynassist_ai_cost_rates"

    __table_args__ = (
        CheckConstraint(
            "input_cost_per_million_micro_usd >= 0",
            name="ck_xynassist_ai_cost_rate_input_nonnegative",
        ),
        CheckConstraint(
            "output_cost_per_million_micro_usd >= 0",
            name="ck_xynassist_ai_cost_rate_output_nonnegative",
        ),
        CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="ck_xynassist_ai_cost_rate_effective_period",
        ),
        Index(
            "ix_xynassist_ai_cost_rate_provider_model",
            "provider",
            "model",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
    )

    provider = Column(
        String(80),
        nullable=False,
        index=True,
    )

    model = Column(
        String(150),
        nullable=False,
        index=True,
    )

    input_cost_per_million_micro_usd = Column(
        Integer,
        nullable=False,
    )

    output_cost_per_million_micro_usd = Column(
        Integer,
        nullable=False,
    )

    effective_from = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    effective_until = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
