"""
Reviewed AI provider/model cost catalog for XynAssist.

This catalog is intentionally separate from customer pricing.

Rates are integer micro-US-dollars per one million tokens. Provider
rates must be verified before being added here. Synchronization must
never invent or infer a provider price.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class CatalogAICostRate:
    provider: str
    model: str
    input_cost_per_million_micro_usd: int
    output_cost_per_million_micro_usd: int


# Only provider/model prices verified and approved through a reviewed
# catalog change belong here.
APPROVED_AI_COST_CATALOG: tuple[
    CatalogAICostRate,
    ...
] = (
    CatalogAICostRate(
        provider="openai",
        model="gpt-5.4-mini",
        input_cost_per_million_micro_usd=750_000,
        output_cost_per_million_micro_usd=4_500_000,
    ),
    CatalogAICostRate(
        provider="openai",
        model="gpt-5.4-mini-2026-03-17",
        input_cost_per_million_micro_usd=750_000,
        output_cost_per_million_micro_usd=4_500_000,
    ),
)


def _normalize_rate(
    rate: CatalogAICostRate,
) -> CatalogAICostRate:
    return CatalogAICostRate(
        provider=(rate.provider or "").strip().lower(),
        model=(rate.model or "").strip(),
        input_cost_per_million_micro_usd=(
            rate.input_cost_per_million_micro_usd
        ),
        output_cost_per_million_micro_usd=(
            rate.output_cost_per_million_micro_usd
        ),
    )


def validate_ai_cost_catalog(
    rates: Iterable[CatalogAICostRate],
) -> tuple[CatalogAICostRate, ...]:
    normalized = tuple(
        _normalize_rate(rate)
        for rate in rates
    )

    seen: set[tuple[str, str]] = set()

    for rate in normalized:
        if not rate.provider:
            raise ValueError(
                "AI cost catalog provider must not be blank"
            )

        if not rate.model:
            raise ValueError(
                "AI cost catalog model must not be blank"
            )

        for field_name, value in (
            (
                "input_cost_per_million_micro_usd",
                rate.input_cost_per_million_micro_usd,
            ),
            (
                "output_cost_per_million_micro_usd",
                rate.output_cost_per_million_micro_usd,
            ),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
            ):
                raise ValueError(
                    f"{field_name} must be an integer"
                )

            if value < 0:
                raise ValueError(
                    f"{field_name} must not be negative"
                )

        key = (
            rate.provider,
            rate.model,
        )

        if key in seen:
            raise ValueError(
                "Duplicate AI cost catalog entry for "
                f"{rate.provider}:{rate.model}"
            )

        seen.add(key)

    return normalized
