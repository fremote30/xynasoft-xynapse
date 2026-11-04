"""
Durable idempotency for XynAssist-owned action execution.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from xynassist_service.models.action_execution import (
    ActionExecution,
)


ACTION_STATUS_COMPLETED = "completed"


class ActionExecutionConflict(Exception):
    """A request_id was reused for different action input."""


class ActionExecutionStateError(Exception):
    """Persisted action execution state is invalid."""


def build_action_fingerprint(
    *,
    action_name: str,
    arguments: dict[str, Any],
) -> str:
    """
    Produce a stable SHA-256 fingerprint of one logical action.
    """

    canonical = json.dumps(
        {
            "action_name": action_name,
            "arguments": arguments,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def _action_lock_key(
    *,
    product: str,
    external_user_id: str,
    request_id: str,
) -> int:
    """Stable signed 64-bit advisory-lock key."""

    raw = (
        f"xynassist-action\x1f"
        f"{product}\x1f"
        f"{external_user_id}\x1f"
        f"{request_id}"
    ).encode("utf-8")

    digest = hashlib.sha256(raw).digest()

    return int.from_bytes(
        digest[:8],
        byteorder="big",
        signed=True,
    )


def _lock_action_request(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    request_id: str,
) -> None:
    """
    Serialize one action request on PostgreSQL.

    The lock is transaction scoped and is automatically released
    on commit or rollback.
    """

    bind = db.get_bind()

    if bind.dialect.name != "postgresql":
        return

    key = _action_lock_key(
        product=product,
        external_user_id=external_user_id,
        request_id=request_id,
    )

    db.execute(
        text(
            "SELECT pg_advisory_xact_lock(:key)"
        ),
        {"key": key},
    )


def _load_execution(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    request_id: str,
) -> ActionExecution | None:
    return db.execute(
        select(ActionExecution).where(
            ActionExecution.product == product,
            ActionExecution.external_user_id
            == external_user_id,
            ActionExecution.request_id
            == request_id,
        )
    ).scalar_one_or_none()


def _decode_result(
    execution: ActionExecution,
) -> dict[str, Any]:
    try:
        result = json.loads(
            execution.result_json
        )
    except (TypeError, ValueError) as exc:
        raise ActionExecutionStateError(
            "Persisted action result is invalid"
        ) from exc

    if not isinstance(result, dict):
        raise ActionExecutionStateError(
            "Persisted action result is invalid"
        )

    return result


def begin_action_execution(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    request_id: str,
    action_name: str,
    arguments: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Establish the durable action idempotency boundary.

    Returns a persisted result for an exact replay. Returns None
    when the caller owns a new logical action and may execute it.

    The caller must keep this transaction open through the
    mutation and complete_action_execution().
    """

    product = product.strip()
    external_user_id = external_user_id.strip()
    action_name = action_name.strip()

    if not product:
        raise ValueError("product is required")

    if not external_user_id:
        raise ValueError(
            "external_user_id is required"
        )

    if not action_name:
        raise ValueError(
            "action_name is required"
        )

    if not isinstance(arguments, dict):
        raise ValueError(
            "arguments must be an object"
        )

    try:
        normalized_request_id = str(
            uuid.UUID(request_id)
        )
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            "request_id must be a UUID"
        ) from exc

    fingerprint = build_action_fingerprint(
        action_name=action_name,
        arguments=arguments,
    )

    _lock_action_request(
        db,
        product=product,
        external_user_id=external_user_id,
        request_id=normalized_request_id,
    )

    existing = _load_execution(
        db,
        product=product,
        external_user_id=external_user_id,
        request_id=normalized_request_id,
    )

    if existing is None:
        return None

    if (
        existing.action_name != action_name
        or existing.request_fingerprint
        != fingerprint
    ):
        raise ActionExecutionConflict(
            "request_id was already used "
            "for different action input"
        )

    if (
        existing.status
        != ACTION_STATUS_COMPLETED
    ):
        raise ActionExecutionStateError(
            "Action execution has invalid state"
        )

    return _decode_result(existing)


def complete_action_execution(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    request_id: str,
    action_name: str,
    arguments: dict[str, Any],
    result: dict[str, Any],
) -> ActionExecution:
    """
    Persist the completed action result in the caller's transaction.
    """

    product = product.strip()
    external_user_id = external_user_id.strip()
    action_name = action_name.strip()

    if not product:
        raise ValueError(
            "product is required"
        )

    if not external_user_id:
        raise ValueError(
            "external_user_id is required"
        )

    if not action_name:
        raise ValueError(
            "action_name is required"
        )

    if not isinstance(arguments, dict):
        raise ValueError(
            "arguments must be an object"
        )

    if not isinstance(result, dict):
        raise ValueError(
            "result must be an object"
        )

    try:
        normalized_request_id = str(
            uuid.UUID(request_id)
        )
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            "request_id must be a UUID"
        ) from exc

    fingerprint = build_action_fingerprint(
        action_name=action_name,
        arguments=arguments,
    )

    execution = ActionExecution(
        product=product,
        external_user_id=external_user_id,
        request_id=normalized_request_id,
        action_name=action_name,
        request_fingerprint=fingerprint,
        status=ACTION_STATUS_COMPLETED,
        result_json=json.dumps(
            result,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ),
        completed_at=func.now(),
    )

    db.add(execution)
    db.flush()

    return execution
