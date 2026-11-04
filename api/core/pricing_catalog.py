"""
Provider-agnostic pricing catalog contracts for XynaFaith V2.

The commercial product catalog defines what XynaFaith sells.
This module defines the structure used to describe approved regional
prices for those products.

Actual launch prices are intentionally not defined here yet.

Design rules:
- pricing is independent from product entitlement definitions
- one commercial plan may have prices in multiple markets
- monthly and annual prices are distinct catalog entries
- money is represented in integer minor currency units
- market and currency codes are normalized uppercase
- historical database prices are not represented by duplicating plans
- payment-provider identifiers do not belong in this catalog
"""

from dataclasses import dataclass
from typing import Iterable

from api.core.product_catalog import COMMERCIAL_PLAN_BY_CODE
from api.models.plan_price import BILLING_INTERVALS


@dataclass(frozen=True)
class CatalogPrice:
    plan_code: str
    market_code: str
    currency: str
    billing_interval: str
    amount_minor: int


# Production pricing remains intentionally empty until launch prices
# are formally approved. Add approved prices here through a reviewed
# catalog change; synchronization commands must not invent prices.
APPROVED_PRICING_CATALOG: tuple[CatalogPrice, ...] = ()


def _normalize_price(price: CatalogPrice) -> CatalogPrice:
    return CatalogPrice(
        plan_code=(price.plan_code or "").strip(),
        market_code=(price.market_code or "").strip().upper(),
        currency=(price.currency or "").strip().upper(),
        billing_interval=(price.billing_interval or "").strip().lower(),
        amount_minor=price.amount_minor,
    )


def validate_pricing_catalog(
    prices: Iterable[CatalogPrice],
) -> tuple[CatalogPrice, ...]:
    """
    Validate and normalize a collection of approved commercial prices.

    The returned tuple is safe for deterministic synchronization.

    Validation deliberately does not inspect the database. Database
    history and effective-period transitions belong to the sync layer.
    """

    normalized = tuple(_normalize_price(price) for price in prices)
    seen_keys: set[tuple[str, str, str]] = set()

    for price in normalized:
        if not price.plan_code:
            raise ValueError("Pricing catalog plan_code must not be blank")

        if price.plan_code not in COMMERCIAL_PLAN_BY_CODE:
            raise ValueError(
                f"Unknown commercial plan in pricing catalog: {price.plan_code}"
            )

        if not price.market_code:
            raise ValueError("Pricing catalog market_code must not be blank")

        if not price.currency:
            raise ValueError("Pricing catalog currency must not be blank")

        if len(price.currency) != 3 or not price.currency.isalpha():
            raise ValueError(
                f"Pricing catalog currency must be a 3-letter code: "
                f"{price.currency}"
            )

        if price.billing_interval not in BILLING_INTERVALS:
            raise ValueError(
                "Unsupported pricing catalog billing interval: "
                f"{price.billing_interval}"
            )

        if isinstance(price.amount_minor, bool) or not isinstance(
            price.amount_minor,
            int,
        ):
            raise ValueError(
                "Pricing catalog amount_minor must be an integer"
            )

        if price.amount_minor < 0:
            raise ValueError(
                "Pricing catalog amount_minor must not be negative"
            )

        key = (
            price.plan_code,
            price.market_code,
            price.billing_interval,
        )

        if key in seen_keys:
            raise ValueError(
                "Duplicate pricing catalog entry for "
                f"{price.plan_code}:{price.market_code}:"
                f"{price.billing_interval}"
            )

        seen_keys.add(key)

    return normalized
