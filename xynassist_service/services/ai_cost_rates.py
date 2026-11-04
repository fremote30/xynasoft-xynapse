"""
Historical AI provider/model cost-rate resolution.

Resolution is exact on provider + model. There is deliberately no
fallback between models or providers and no inferred pricing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from xynassist_service.models.ai_cost_rate import (
    AICostRate,
)


class AICostRateError(Exception):
    """Base error for AI cost-rate resolution."""


class AICostRateNotFound(AICostRateError):
    """No rate applies to the requested provider/model/time."""


class AICostRateConfigurationError(AICostRateError):
    """Multiple rates apply to one provider/model/time."""


@dataclass(frozen=True)
class ResolvedAICostRate:
    rate_id: int
    provider: str
    model: str
    input_cost_per_million_micro_usd: int
    output_cost_per_million_micro_usd: int
    effective_from: datetime
    effective_until: datetime | None


def resolve_ai_cost_rate(
    db: Session,
    *,
    provider: str,
    model: str,
    occurred_at: datetime,
) -> ResolvedAICostRate:
    normalized_provider = (
        provider or ""
    ).strip().lower()

    normalized_model = (
        model or ""
    ).strip()

    if not normalized_provider:
        raise ValueError(
            "provider must not be blank"
        )

    if not normalized_model:
        raise ValueError(
            "model must not be blank"
        )

    if occurred_at is None:
        raise ValueError(
            "occurred_at is required"
        )

    rows = (
        db.query(AICostRate)
        .filter(
            AICostRate.provider
            == normalized_provider,
            AICostRate.model
            == normalized_model,
            AICostRate.effective_from
            <= occurred_at,
            (
                AICostRate.effective_until.is_(None)
                | (
                    AICostRate.effective_until
                    > occurred_at
                )
            ),
        )
        .order_by(
            AICostRate.effective_from.desc(),
            AICostRate.id.desc(),
        )
        .all()
    )

    if not rows:
        raise AICostRateNotFound(
            "No AI cost rate found for "
            f"{normalized_provider}:{normalized_model}"
        )

    if len(rows) > 1:
        raise AICostRateConfigurationError(
            "Multiple AI cost rates apply to "
            f"{normalized_provider}:{normalized_model}"
        )

    row = rows[0]

    return ResolvedAICostRate(
        rate_id=row.id,
        provider=row.provider,
        model=row.model,
        input_cost_per_million_micro_usd=(
            row.input_cost_per_million_micro_usd
        ),
        output_cost_per_million_micro_usd=(
            row.output_cost_per_million_micro_usd
        ),
        effective_from=row.effective_from,
        effective_until=row.effective_until,
    )
