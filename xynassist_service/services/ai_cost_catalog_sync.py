"""
Synchronize reviewed AI cost catalog entries while preserving history.

Rules:
- caller owns transaction
- historical rows are never deleted
- unchanged current rates remain untouched
- changed current rates close at the transition boundary
- a new current row is created for the replacement
- ambiguous current rows fail closed
- future scheduled rows fail closed
- catalog omission leaves stored history/current rows untouched
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy.orm import Session

from xynassist_service.core.ai_cost_catalog import (
    CatalogAICostRate,
    validate_ai_cost_catalog,
)
from xynassist_service.models.ai_cost_rate import (
    AICostRate,
)


class AICostCatalogSyncError(Exception):
    """Base error for AI cost catalog synchronization."""


class AICostCatalogConfigurationError(
    AICostCatalogSyncError
):
    """Stored cost-rate state is ambiguous."""


@dataclass(frozen=True)
class AICostCatalogSyncResult:
    rates_created: int = 0
    rates_transitioned: int = 0
    rates_unchanged: int = 0


def sync_ai_cost_catalog(
    db: Session,
    *,
    rates: Iterable[CatalogAICostRate],
    now: datetime | None = None,
) -> AICostCatalogSyncResult:
    catalog = validate_ai_cost_catalog(rates)
    now = now or datetime.now(timezone.utc)

    created = 0
    transitioned = 0
    unchanged = 0

    for desired in catalog:
        future_rows = (
            db.query(AICostRate)
            .filter(
                AICostRate.provider
                == desired.provider,
                AICostRate.model
                == desired.model,
                AICostRate.effective_from
                > now,
                AICostRate.effective_until.is_(None),
            )
            .all()
        )

        if future_rows:
            raise AICostCatalogConfigurationError(
                "Future AI cost rate already exists for "
                f"{desired.provider}:{desired.model}"
            )

        current_rows = (
            db.query(AICostRate)
            .filter(
                AICostRate.provider
                == desired.provider,
                AICostRate.model
                == desired.model,
                AICostRate.effective_from
                <= now,
                (
                    AICostRate.effective_until.is_(None)
                    | (
                        AICostRate.effective_until
                        > now
                    )
                ),
            )
            .order_by(
                AICostRate.effective_from.desc(),
                AICostRate.id.desc(),
            )
            .all()
        )

        if len(current_rows) > 1:
            raise AICostCatalogConfigurationError(
                "Multiple current AI cost rates exist for "
                f"{desired.provider}:{desired.model}"
            )

        current = (
            current_rows[0]
            if current_rows
            else None
        )

        desired_values = (
            desired.input_cost_per_million_micro_usd,
            desired.output_cost_per_million_micro_usd,
        )

        if current is not None:
            current_values = (
                current.input_cost_per_million_micro_usd,
                current.output_cost_per_million_micro_usd,
            )

            if current_values == desired_values:
                unchanged += 1
                continue

            current.effective_until = now
            transitioned += 1

        db.add(
            AICostRate(
                provider=desired.provider,
                model=desired.model,
                input_cost_per_million_micro_usd=(
                    desired.input_cost_per_million_micro_usd
                ),
                output_cost_per_million_micro_usd=(
                    desired.output_cost_per_million_micro_usd
                ),
                effective_from=now,
            )
        )

        created += 1

    db.flush()

    return AICostCatalogSyncResult(
        rates_created=created,
        rates_transitioned=transitioned,
        rates_unchanged=unchanged,
    )
