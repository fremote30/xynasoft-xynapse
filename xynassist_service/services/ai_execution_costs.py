"""
Deterministic cost calculation for immutable XynAssist AI executions.

AIExecution records factual provider/model/token telemetry.
AICostRate records historical provider pricing.

This service joins those two facts without mutating either one.

Money is returned as integer micro-US-dollars:
    1 USD = 1_000_000 micro-USD.

Fractional micro-USD results are rounded upward so provider cost is
never understated.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from xynassist_service.models.ai_execution import AIExecution
from xynassist_service.services.ai_cost_rates import (
    ResolvedAICostRate,
    resolve_ai_cost_rate,
)


TOKENS_PER_MILLION = 1_000_000


class AIExecutionCostError(Exception):
    """Base error for execution cost calculation."""


class AIExecutionUsageMissing(AIExecutionCostError):
    """Execution lacks token telemetry required for cost calculation."""


@dataclass(frozen=True)
class CalculatedAIExecutionCost:
    execution_id: str
    rate_id: int
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    input_cost_micro_usd: int
    output_cost_micro_usd: int
    total_cost_micro_usd: int


def _ceil_div(
    numerator: int,
    denominator: int,
) -> int:
    if denominator <= 0:
        raise ValueError(
            "denominator must be positive"
        )

    return (
        numerator + denominator - 1
    ) // denominator


def _token_cost_micro_usd(
    *,
    tokens: int,
    rate_per_million_micro_usd: int,
) -> int:
    if tokens < 0:
        raise ValueError(
            "tokens must not be negative"
        )

    if rate_per_million_micro_usd < 0:
        raise ValueError(
            "rate must not be negative"
        )

    if tokens == 0 or rate_per_million_micro_usd == 0:
        return 0

    return _ceil_div(
        tokens * rate_per_million_micro_usd,
        TOKENS_PER_MILLION,
    )


def calculate_ai_execution_cost(
    db: Session,
    *,
    execution: AIExecution,
) -> CalculatedAIExecutionCost:
    """
    Calculate historical provider cost for one physical execution.

    The rate is resolved using the execution's provider-returned model
    identifier and the rate effective at execution.created_at.
    """

    if execution.input_tokens is None:
        raise AIExecutionUsageMissing(
            "AI execution is missing input token telemetry"
        )

    if execution.output_tokens is None:
        raise AIExecutionUsageMissing(
            "AI execution is missing output token telemetry"
        )

    if execution.created_at is None:
        raise AIExecutionCostError(
            "AI execution is missing created_at"
        )

    rate: ResolvedAICostRate = resolve_ai_cost_rate(
        db,
        provider=execution.provider,
        model=execution.model,
        occurred_at=execution.created_at,
    )

    input_cost = _token_cost_micro_usd(
        tokens=execution.input_tokens,
        rate_per_million_micro_usd=(
            rate.input_cost_per_million_micro_usd
        ),
    )

    output_cost = _token_cost_micro_usd(
        tokens=execution.output_tokens,
        rate_per_million_micro_usd=(
            rate.output_cost_per_million_micro_usd
        ),
    )

    return CalculatedAIExecutionCost(
        execution_id=execution.id,
        rate_id=rate.rate_id,
        provider=execution.provider,
        model=execution.model,
        input_tokens=execution.input_tokens,
        output_tokens=execution.output_tokens,
        input_cost_micro_usd=input_cost,
        output_cost_micro_usd=output_cost,
        total_cost_micro_usd=(
            input_cost + output_cost
        ),
    )
