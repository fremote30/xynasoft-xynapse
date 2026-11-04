"""
Provider-agnostic commercial price resolution for XynaFaith V2.

This service answers one question:

    What price is currently sellable for this plan, market, and
    billing interval?

It deliberately does not:
- perform currency conversion
- inspect payment-provider identifiers
- create subscriptions
- mutate pricing rows
- infer a different billing interval

Resolution rules:
1. plan must exist and be active
2. only active price rows are eligible
3. effective_from <= now < effective_until
4. exact requested market wins
5. GLOBAL is fallback only when no exact-market price is current
6. billing intervals never substitute for one another
7. multiple current rows at the same resolution level are a
   configuration error
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from api.models.plan import Plan
from api.models.plan_price import BILLING_INTERVALS, PlanPrice


GLOBAL_MARKET_CODE = "GLOBAL"


class PriceResolutionError(Exception):
    """Base exception for commercial price resolution."""


class PriceNotFound(PriceResolutionError):
    """No currently sellable price exists for the requested product."""


class PriceConfigurationError(PriceResolutionError):
    """Stored pricing data is ambiguous or invalid for resolution."""


@dataclass(frozen=True)
class ResolvedPlanPrice:
    plan_id: int
    plan_code: str
    market_code: str
    requested_market_code: str
    currency: str
    billing_interval: str
    amount_minor: int
    price_id: int
    used_global_fallback: bool


def _normalize_market_code(market_code: str) -> str:
    value = (market_code or "").strip().upper()

    if not value:
        raise ValueError("market_code must not be blank")

    return value


def _normalize_billing_interval(billing_interval: str) -> str:
    value = (billing_interval or "").strip().lower()

    if value not in BILLING_INTERVALS:
        raise ValueError(
            f"Unsupported billing interval: {billing_interval}"
        )

    return value


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


def _require_unambiguous(
    rows: list[PlanPrice],
    *,
    plan_code: str,
    market_code: str,
    billing_interval: str,
) -> Optional[PlanPrice]:
    if not rows:
        return None

    if len(rows) > 1:
        raise PriceConfigurationError(
            "Multiple current prices exist for "
            f"{plan_code}:{market_code}:{billing_interval}"
        )

    return rows[0]


def resolve_plan_price(
    db: Session,
    *,
    plan_code: str,
    market_code: str,
    billing_interval: str,
    now: Optional[datetime] = None,
) -> ResolvedPlanPrice:
    """
    Resolve the currently sellable price for a commercial plan.

    Exact market pricing takes precedence over GLOBAL fallback.
    """

    normalized_plan_code = (plan_code or "").strip()

    if not normalized_plan_code:
        raise ValueError("plan_code must not be blank")

    requested_market = _normalize_market_code(market_code)
    interval = _normalize_billing_interval(billing_interval)
    now = now or datetime.utcnow()

    plan = (
        db.query(Plan)
        .filter(
            Plan.code == normalized_plan_code,
            Plan.is_active.is_(True),
        )
        .one_or_none()
    )

    if plan is None:
        raise PriceNotFound(
            f"No active commercial plan found for {normalized_plan_code}"
        )

    exact_rows = _current_prices(
        db,
        plan_id=plan.id,
        market_code=requested_market,
        billing_interval=interval,
        now=now,
    )

    exact = _require_unambiguous(
        exact_rows,
        plan_code=plan.code,
        market_code=requested_market,
        billing_interval=interval,
    )

    selected = exact
    used_global_fallback = False

    if selected is None and requested_market != GLOBAL_MARKET_CODE:
        global_rows = _current_prices(
            db,
            plan_id=plan.id,
            market_code=GLOBAL_MARKET_CODE,
            billing_interval=interval,
            now=now,
        )

        selected = _require_unambiguous(
            global_rows,
            plan_code=plan.code,
            market_code=GLOBAL_MARKET_CODE,
            billing_interval=interval,
        )

        used_global_fallback = selected is not None

    if selected is None:
        raise PriceNotFound(
            "No current price found for "
            f"{plan.code}:{requested_market}:{interval}"
        )

    return ResolvedPlanPrice(
        plan_id=plan.id,
        plan_code=plan.code,
        market_code=selected.market_code,
        requested_market_code=requested_market,
        currency=selected.currency,
        billing_interval=selected.billing_interval,
        amount_minor=selected.amount_minor,
        price_id=selected.id,
        used_global_fallback=used_global_fallback,
    )
