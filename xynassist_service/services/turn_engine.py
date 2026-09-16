"""
XynAssist conversation turn engine boundary.

This boundary connects durable conversation-turn execution to the
Xyniva intelligence orchestrator. Provider selection and construction
remain outside domain orchestration.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from xynassist_service.ai.bootstrap import (
    get_configured_model_provider,
)
from xynassist_service.services.context_assembly import (
    XynivaContextBundle,
)
from xynassist_service.xyniva.orchestrator import (
    execute_xyniva_turn,
)


@dataclass(frozen=True)
class TurnEngineResult:
    content: str
    skill: str | None = None
    action: dict[str, Any] | None = None
    prompt: str | None = None


def execute_turn_engine(
    *,
    content: str,
    context: dict[str, Any] | None,
    context_bundle: XynivaContextBundle | None = None,
) -> TurnEngineResult:
    """
    Execute one Xyniva intelligence turn.

    Durable request idempotency, processing leases, persistence, and
    failure handling are owned by the surrounding turn service.
    """

    provider = get_configured_model_provider()

    result = execute_xyniva_turn(
        content=content,
        context=context,
        context_bundle=context_bundle,
        provider_name=provider.name,
    )

    return TurnEngineResult(
        content=result.content,
        skill=result.skill,
        action=result.action,
        prompt=result.prompt,
    )
