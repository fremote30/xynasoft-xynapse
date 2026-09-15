"""
XynAssist conversation turn engine boundary.

The current implementation is deliberately deterministic and exists
only to establish the persistence/idempotency HTTP contract. Real
model routing and ministry skills will replace this implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
) -> TurnEngineResult:
    """
    Temporary deterministic engine.

    This is NOT the production Xyniva intelligence layer.
    """

    return TurnEngineResult(
        content=(
            "XynAssist received your message. "
            "AI orchestration is not yet configured."
        ),
        skill="conversation.respond",
    )
