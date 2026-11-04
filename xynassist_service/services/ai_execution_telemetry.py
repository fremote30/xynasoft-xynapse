"""
Append-only persistence for factual AI provider execution telemetry.

This service records provider execution facts only. It does not own
commercial quota accounting, provider pricing, prompts, responses,
or logical-request idempotency.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from xynassist_service.models.ai_execution import AIExecution


def record_ai_execution(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    request_id: str,
    operation: str,
    provider: str,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    attempt_number: int = 1,
) -> AIExecution:
    """Append one factual model-provider execution."""

    values = {
        "product": product.strip(),
        "external_user_id": external_user_id.strip(),
        "request_id": request_id.strip(),
        "operation": operation.strip(),
        "provider": provider.strip(),
        "model": model.strip(),
    }

    for name, value in values.items():
        if not value:
            raise ValueError(
                f"{name} is required for AI execution telemetry"
            )

    try:
        normalized_request_id = str(
            uuid.UUID(values["request_id"])
        )
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            "request_id must be a valid UUID"
        ) from exc

    if input_tokens is not None and input_tokens < 0:
        raise ValueError("input_tokens cannot be negative")

    if output_tokens is not None and output_tokens < 0:
        raise ValueError("output_tokens cannot be negative")

    if attempt_number < 1:
        raise ValueError("attempt_number must be at least 1")

    execution = AIExecution(
        product=values["product"],
        external_user_id=values["external_user_id"],
        request_id=normalized_request_id,
        operation=values["operation"],
        provider=values["provider"],
        model=values["model"],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        attempt_number=attempt_number,
    )

    db.add(execution)
    db.flush()

    return execution
