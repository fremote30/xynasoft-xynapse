"""
Synchronize approved XynaFaith pricing catalog entries into PlanPrice history.

The pricing catalog describes desired current commercial prices. This service
reconciles those entries without destroying historical pricing.

Rules:
- transaction ownership belongs to the caller; this service never commits
- commercial Plan creation belongs to product catalog synchronization
- missing or inactive referenced Plans fail closed
- existing historical PlanPrice rows are never deleted
- unchanged current prices remain untouched
- changed current prices are closed at the transition boundary and succeeded
  by a new current row
- multiple current rows for one catalog key fail closed
- active future-scheduled prices for a catalog key fail closed
- catalog omission does not deactivate or delete an existing price
- subscriptions and payment-provider state are never modified
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from api.core.pricing_catalog import CatalogPrice, validate_pricing_catalog
from api.models.plan import Plan
from api.models.plan_price import PlanPrice


class PricingCatalogSyncError(Exception):
    """Base exception for pricing catalog synchronization."""


class PricingCatalogPlanError(PricingCatalogSyncError):
    """A catalog price references a missing or inactive commercial Plan."""


class PricingCatalogConfigurationError(PricingCatalogSyncError):
    """Stored pricing is ambiguous for a catalog-owned current price."""


@dataclass(frozen=True)
class PricingCatalogSyncResult:
    prices_created: int = 0
    prices_transitioned: int = 0
    prices_unchanged: int = 0


def _current_prices(
    db: Session,
    *,
    plan_id: int,
    market_code: str,
    billing_interval: str,
    now: datetime,
) -> list[PlanPrice]:
    return (
        db.query(PlanPrice)
        .filter(
            PlanPrice.plan_id == plan_id,
            PlanPrice.market_code == market_code,
            PlanPrice.billing_interval == billing_interval,
            PlanPrice.is_active.is_(True),
            PlanPrice.effective_from <= now,
            (
                PlanPrice.effective_until.is_(None)
                | (PlanPrice.effective_until > now)
            ),
        )
        .order_by(
            PlanPrice.effective_from.desc(),
            PlanPrice.id.desc(),
        )
        .all()
    )


def _future_prices(
    db: Session,
    *,
    plan_id: int,
    market_code: str,
    billing_interval: str,
    now: datetime,
) -> list[PlanPrice]:
    return (
        db.query(PlanPrice)
        .filter(
            PlanPrice.plan_id == plan_id,
            PlanPrice.market_code == market_code,
            PlanPrice.billing_interval == billing_interval,
            PlanPrice.is_active.is_(True),
            PlanPrice.effective_from > now,
        )
        .order_by(
            PlanPrice.effective_from.asc(),
            PlanPrice.id.asc(),
        )
        .all()
    )


def _require_active_plan(
    db: Session,
    *,
    plan_code: str,
) -> Plan:
    plan = (
        db.query(Plan)
        .filter(Plan.code == plan_code)
        .one_or_none()
    )

    if plan is None:
        raise PricingCatalogPlanError(
            f"Pricing catalog references missing plan: {plan_code}"
        )

    if not plan.is_active:
        raise PricingCatalogPlanError(
            f"Pricing catalog references inactive plan: {plan_code}"
        )

    return plan


def _sync_price(
    db: Session,
    *,
    desired: CatalogPrice,
    now: datetime,
) -> tuple[int, int, int]:
    plan = _require_active_plan(
        db,
        plan_code=desired.plan_code,
    )

    current = _current_prices(
        db,
        plan_id=plan.id,
        market_code=desired.market_code,
        billing_interval=desired.billing_interval,
        now=now,
    )

    if len(current) > 1:
        raise PricingCatalogConfigurationError(
            "Multiple current prices exist for "
            f"{desired.plan_code}:{desired.market_code}:"
            f"{desired.billing_interval}"
        )

    future = _future_prices(
        db,
        plan_id=plan.id,
        market_code=desired.market_code,
        billing_interval=desired.billing_interval,
        now=now,
    )

    if future:
        raise PricingCatalogConfigurationError(
            "Active future-scheduled price exists for "
            f"{desired.plan_code}:{desired.market_code}:"
            f"{desired.billing_interval}"
        )

    if not current:
        db.add(
            PlanPrice(
                plan_id=plan.id,
                market_code=desired.market_code,
                currency=desired.currency,
                billing_interval=desired.billing_interval,
                amount_minor=desired.amount_minor,
                is_active=True,
                effective_from=now,
                effective_until=None,
            )
        )
        db.flush()
        return (1, 0, 0)

    existing = current[0]

    if (
        existing.currency == desired.currency
        and existing.amount_minor == desired.amount_minor
    ):
        return (0, 0, 1)

    # Preserve the old row as historical data and begin the successor at the
    # exact same boundary. effective_until is exclusive in price resolution.
    existing.effective_until = now

    db.add(
        PlanPrice(
            plan_id=plan.id,
            market_code=desired.market_code,
            currency=desired.currency,
            billing_interval=desired.billing_interval,
            amount_minor=desired.amount_minor,
            is_active=True,
            effective_from=now,
            effective_until=None,
        )
    )

    db.flush()
    return (1, 1, 0)


def sync_pricing_catalog(
    db: Session,
    prices: Iterable[CatalogPrice],
    *,
    now: Optional[datetime] = None,
) -> PricingCatalogSyncResult:
    """
    Reconcile approved pricing entries while preserving price history.

    Catalog omission is intentionally not interpreted as price removal.
    Transaction ownership belongs to the caller.
    """

    desired_prices = validate_pricing_catalog(prices)
    transition_time = now or datetime.utcnow()

    created = 0
    transitioned = 0
    unchanged = 0

    for desired in desired_prices:
        result = _sync_price(
            db,
            desired=desired,
            now=transition_time,
        )
        created += result[0]
        transitioned += result[1]
        unchanged += result[2]

    return PricingCatalogSyncResult(
        prices_created=created,
        prices_transitioned=transitioned,
        prices_unchanged=unchanged,
    )
