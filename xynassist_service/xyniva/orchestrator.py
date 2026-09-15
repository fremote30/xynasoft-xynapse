"""
Xyniva conversational orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from xynassist_service.ai.contracts import (
    ModelMessage,
    ModelRequest,
)
from xynassist_service.ai.registry import get_model_provider
from xynassist_service.xyniva.policy import XYNIVA_SYSTEM_POLICY


@dataclass(frozen=True)
class XynivaResult:
    content: str
    skill: str
    action: dict[str, Any] | None = None
    prompt: str | None = None
    provider: str | None = None
    model: str | None = None


def _context_instruction(
    context: dict[str, Any] | None,
) -> str | None:
    if not context:
        return None

    allowed = {}

    for key in (
        "denomination",
        "audience",
        "language",
        "church_name",
    ):
        value = context.get(key)

        if isinstance(value, str) and value.strip():
            allowed[key] = value.strip()

    if not allowed:
        return None

    lines = [
        "Use the following trusted product context when relevant:"
    ]

    for key, value in allowed.items():
        lines.append(f"- {key}: {value}")

    return "\n".join(lines)


def execute_xyniva_turn(
    *,
    content: str,
    context: dict[str, Any] | None,
    provider_name: str,
) -> XynivaResult:
    user_content = content.strip()

    if not user_content:
        raise ValueError("Turn content is required")

    messages = [
        ModelMessage(
            role="system",
            content=XYNIVA_SYSTEM_POLICY,
        )
    ]

    context_instruction = _context_instruction(context)

    if context_instruction:
        messages.append(
            ModelMessage(
                role="system",
                content=context_instruction,
            )
        )

    messages.append(
        ModelMessage(
            role="user",
            content=user_content,
        )
    )

    provider = get_model_provider(provider_name)

    response = provider.generate(
        ModelRequest(
            messages=messages,
            temperature=0.2,
            max_output_tokens=1200,
        )
    )

    response_content = response.content.strip()

    if not response_content:
        raise RuntimeError(
            "Model provider returned an empty response"
        )

    return XynivaResult(
        content=response_content,
        skill="conversation.respond",
        provider=response.provider,
        model=response.model,
    )
