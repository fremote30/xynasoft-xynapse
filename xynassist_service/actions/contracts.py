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
    "service_assignment.create": ActionDefinition(
        name="service_assignment.create",
        product="xynafaith",
        confirmation="required",
    ),
    "service_assignment.reassign": ActionDefinition(
        name="service_assignment.reassign",
        product="xynafaith",
        confirmation="required",
    ),
    "service_assignment.update_status": ActionDefinition(
        name="service_assignment.update_status",
        product="xynafaith",
        confirmation="required",
    ),
    "announcement.save_draft": ActionDefinition(
        name="announcement.save_draft",
        product="xynafaith",
        confirmation="none",
    ),
    "event.save_draft": ActionDefinition(
        name="event.save_draft",
        product="xynafaith",
        confirmation="none",
    ),
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
