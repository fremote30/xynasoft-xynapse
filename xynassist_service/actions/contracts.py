"""
Central contracts for actions XynAssist may propose.

XynAssist proposes actions only. The receiving product remains
authoritative for authentication, authorization, validation,
confirmation, idempotency, and execution.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


ConfirmationPolicy = Literal[
    "none",
    "required",
]


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    product: str
    confirmation: ConfirmationPolicy


ACTION_DEFINITIONS: dict[str, ActionDefinition] = {
    "sermon.save": ActionDefinition(
        name="sermon.save",
        product="xynafaith",
        confirmation="none",
    ),
    "sermon.update": ActionDefinition(
        name="sermon.update",
        product="xynafaith",
        confirmation="none",
    ),
    "sermon.delete": ActionDefinition(
        name="sermon.delete",
        product="xynafaith",
        confirmation="required",
    ),
    "memory.remember": ActionDefinition(
        name="memory.remember",
        product="xynafaith",
        confirmation="none",
    ),
    "memory.forget": ActionDefinition(
        name="memory.forget",
        product="xynafaith",
        confirmation="required",
    ),
}


def get_action_definition(
    name: str,
) -> ActionDefinition | None:
    return ACTION_DEFINITIONS.get(name)


def is_supported_action(
    name: str,
    *,
    product: str | None = None,
) -> bool:
    definition = get_action_definition(name)

    if definition is None:
        return False

    if product is not None:
        return definition.product == product

    return True
