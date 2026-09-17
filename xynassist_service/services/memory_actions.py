"""
Trusted execution of XynAssist-owned persistent-memory actions.

The model may propose an action, but trusted product identity and
confirmation are supplied independently by the integration layer.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from xynassist_service.services.action_executions import (
    begin_action_execution,
    complete_action_execution,
)
from xynassist_service.services.memories import (
    ALLOWED_MEMORY_TYPES,
    create_or_update_memory,
    deactivate_memory_by_identity,
)


MEMORY_REMEMBER = "memory.remember"
MEMORY_FORGET = "memory.forget"

SUPPORTED_MEMORY_ACTIONS = frozenset(
    {
        MEMORY_REMEMBER,
        MEMORY_FORGET,
    }
)


class MemoryActionConfirmationRequired(Exception):
    """Trusted confirmation is required before execution."""


class MemoryActionTargetNotFound(Exception):
    """The requested active memory does not exist."""


def _required_string(
    value: Any,
    field: str,
) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} is required")

    normalized = value.strip()

    if not normalized:
        raise ValueError(f"{field} is required")

    return normalized


def _validate_arguments(
    *,
    action_name: str,
    arguments: dict[str, Any],
) -> dict[str, str]:
    if not isinstance(arguments, dict):
        raise ValueError(
            "arguments must be an object"
        )

    if action_name == MEMORY_REMEMBER:
        expected = {
            "memory_type",
            "key",
            "value",
        }

        if set(arguments) != expected:
            raise ValueError(
                "Invalid memory.remember arguments"
            )

        memory_type = _required_string(
            arguments.get("memory_type"),
            "memory_type",
        )
        key = _required_string(
            arguments.get("key"),
            "key",
        )
        value = _required_string(
            arguments.get("value"),
            "value",
        )

        if memory_type not in ALLOWED_MEMORY_TYPES:
            raise ValueError(
                "Unsupported memory type"
            )

        return {
            "memory_type": memory_type,
            "key": key,
            "value": value,
        }

    if action_name == MEMORY_FORGET:
        expected = {
            "memory_type",
            "key",
        }

        if set(arguments) != expected:
            raise ValueError(
                "Invalid memory.forget arguments"
            )

        memory_type = _required_string(
            arguments.get("memory_type"),
            "memory_type",
        )
        key = _required_string(
            arguments.get("key"),
            "key",
        )

        if memory_type not in ALLOWED_MEMORY_TYPES:
            raise ValueError(
                "Unsupported memory type"
            )

        return {
            "memory_type": memory_type,
            "key": key,
        }

    raise ValueError(
        "Unsupported memory action"
    )


def execute_memory_action(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    request_id: str,
    action_name: str,
    arguments: dict[str, Any],
    trusted_confirmed: bool = False,
) -> dict[str, Any]:
    """
    Execute one trusted XynAssist-owned memory action.

    The caller owns transaction commit/rollback.

    Exact completed retries replay before target-state inspection.
    Confirmation is trusted integration state, never an action argument.
    """

    if action_name not in SUPPORTED_MEMORY_ACTIONS:
        raise ValueError(
            "Unsupported memory action"
        )

    validated_arguments = _validate_arguments(
        action_name=action_name,
        arguments=arguments,
    )

    replay = begin_action_execution(
        db,
        product=product,
        external_user_id=external_user_id,
        request_id=request_id,
        action_name=action_name,
        arguments=validated_arguments,
    )

    if replay is not None:
        return replay

    if action_name == MEMORY_REMEMBER:
        memory = create_or_update_memory(
            db,
            product=product,
            external_user_id=external_user_id,
            memory_type=(
                validated_arguments["memory_type"]
            ),
            key=validated_arguments["key"],
            value=validated_arguments["value"],
            source="explicit_user",
        )

        result = {
            "memory_id": memory.id,
            "memory_type": memory.memory_type,
            "key": memory.key,
            "status": memory.status,
        }

    else:
        if trusted_confirmed is not True:
            raise MemoryActionConfirmationRequired(
                "Trusted confirmation is required"
            )

        memory = deactivate_memory_by_identity(
            db,
            product=product,
            external_user_id=external_user_id,
            memory_type=(
                validated_arguments["memory_type"]
            ),
            key=validated_arguments["key"],
        )

        if memory is None:
            raise MemoryActionTargetNotFound(
                "Memory not found"
            )

        result = {
            "memory_id": memory.id,
            "memory_type": memory.memory_type,
            "key": memory.key,
            "status": memory.status,
        }

    complete_action_execution(
        db,
        product=product,
        external_user_id=external_user_id,
        request_id=request_id,
        action_name=action_name,
        arguments=validated_arguments,
        result=result,
    )

    return result
