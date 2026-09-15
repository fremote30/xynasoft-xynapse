"""
Durable idempotency primitives for XynAssist conversation turns.

This layer owns request identity and replay safety. It does not
perform AI execution.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from xynassist_service.models.conversation_turn import (
    ConversationTurn,
)


TURN_STATUS_PROCESSING = "processing"
TURN_STATUS_COMPLETED = "completed"
TURN_STATUS_FAILED = "failed"


class TurnIdempotencyError(Exception):
    """Base error for turn idempotency."""


class TurnRequestConflict(TurnIdempotencyError):
    """
    A request_id was reused with different logical input.
    """


class TurnRequestInProgress(TurnIdempotencyError):
    """
    The same logical request is already being processed.
    """


class TurnRequestStateError(TurnIdempotencyError):
    """
    Persisted turn state is internally inconsistent.
    """


@dataclass(frozen=True)
class TurnClaim:
    turn: ConversationTurn
    replay_response: dict[str, Any] | None

    @property
    def is_replay(self) -> bool:
        return self.replay_response is not None


def build_request_fingerprint(
    *,
    conversation_id: str,
    content: str,
    context: dict[str, Any] | None,
) -> str:
    """
    Produce a stable SHA-256 fingerprint of the logical request.

    Canonical JSON prevents dictionary key order from changing the
    fingerprint.
    """

    canonical = json.dumps(
        {
            "conversation_id": conversation_id,
            "content": content,
            "context": context,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()


def _request_lock_key(
    *,
    product: str,
    external_user_id: str,
    request_id: str,
) -> int:
    """
    Stable signed 64-bit key for PostgreSQL advisory locking.
    """

    raw = (
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


def _lock_request(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    request_id: str,
) -> None:
    """
    Serialize claims for the same logical request on PostgreSQL.

    SQLite unit tests rely on the unique constraint instead.
    """

    bind = db.get_bind()

    if bind.dialect.name != "postgresql":
        return

    key = _request_lock_key(
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


def _load_turn(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    request_id: str,
) -> ConversationTurn | None:
    stmt = select(
        ConversationTurn
    ).where(
        ConversationTurn.product == product,
        ConversationTurn.external_user_id
        == external_user_id,
        ConversationTurn.request_id
        == request_id,
    )

    return db.execute(
        stmt
    ).scalar_one_or_none()


def _decode_response(
    turn: ConversationTurn,
) -> dict[str, Any]:
    if not turn.response_json:
        raise TurnRequestStateError(
            "Completed turn has no persisted response"
        )

    try:
        value = json.loads(
            turn.response_json
        )
    except (TypeError, ValueError) as exc:
        raise TurnRequestStateError(
            "Completed turn response is invalid"
        ) from exc

    if not isinstance(value, dict):
        raise TurnRequestStateError(
            "Completed turn response is invalid"
        )

    return value


def claim_turn_request(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    conversation_id: str,
    request_id: str,
    content: str,
    context: dict[str, Any] | None,
) -> TurnClaim:
    """
    Claim one logical turn.

    New request:
        creates processing state.

    Same completed request:
        returns the persisted response.

    Same request_id with different input:
        raises TurnRequestConflict.

    Same request still processing:
        raises TurnRequestInProgress.

    Failed requests currently fail closed rather than automatically
    retrying model execution. Retry semantics will be introduced
    deliberately at the orchestration layer.
    """

    product = product.strip()
    external_user_id = external_user_id.strip()
    conversation_id = conversation_id.strip()
    request_id = request_id.strip()
    content = content.strip()

    if not product:
        raise ValueError(
            "product is required"
        )

    if not external_user_id:
        raise ValueError(
            "external_user_id is required"
        )

    if not conversation_id:
        raise ValueError(
            "conversation_id is required"
        )

    if not content:
        raise ValueError(
            "content is required"
        )

    try:
        normalized_request_id = str(
            uuid.UUID(request_id)
        )
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            "request_id must be a UUID"
        ) from exc

    fingerprint = build_request_fingerprint(
        conversation_id=conversation_id,
        content=content,
        context=context,
    )

    _lock_request(
        db,
        product=product,
        external_user_id=external_user_id,
        request_id=normalized_request_id,
    )

    existing = _load_turn(
        db,
        product=product,
        external_user_id=external_user_id,
        request_id=normalized_request_id,
    )

    if existing is not None:
        if (
            existing.conversation_id
            != conversation_id
            or existing.request_fingerprint
            != fingerprint
        ):
            raise TurnRequestConflict(
                "request_id was already used "
                "for different turn input"
            )

        if (
            existing.status
            == TURN_STATUS_COMPLETED
        ):
            return TurnClaim(
                turn=existing,
                replay_response=(
                    _decode_response(existing)
                ),
            )

        if (
            existing.status
            == TURN_STATUS_PROCESSING
        ):
            raise TurnRequestInProgress(
                "turn request is already processing"
            )

        if existing.status == TURN_STATUS_FAILED:
            raise TurnRequestStateError(
                "turn request previously failed"
            )

        raise TurnRequestStateError(
            "turn request has unknown state"
        )

    turn = ConversationTurn(
        id=str(uuid.uuid4()),
        product=product,
        external_user_id=external_user_id,
        conversation_id=conversation_id,
        request_id=normalized_request_id,
        request_fingerprint=fingerprint,
        status=TURN_STATUS_PROCESSING,
    )

    db.add(turn)

    try:
        db.flush()
    except IntegrityError:
        # PostgreSQL callers are protected by the advisory lock.
        # This path primarily protects other SQL dialects and any
        # unexpected uniqueness race.
        db.rollback()
        raise TurnRequestInProgress(
            "turn request was claimed concurrently"
        )

    return TurnClaim(
        turn=turn,
        replay_response=None,
    )


def complete_turn_request(
    db: Session,
    *,
    turn: ConversationTurn,
    response: dict[str, Any],
    user_message_id: str,
    assistant_message_id: str,
) -> None:
    if turn.status == TURN_STATUS_COMPLETED:
        persisted = _decode_response(turn)

        if persisted != response:
            raise TurnRequestStateError(
                "completed turn response mismatch"
            )

        return

    if turn.status != TURN_STATUS_PROCESSING:
        raise TurnRequestStateError(
            "only processing turns can complete"
        )

    turn.user_message_id = user_message_id
    turn.assistant_message_id = (
        assistant_message_id
    )
    turn.response_json = json.dumps(
        response,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    turn.status = TURN_STATUS_COMPLETED
    turn.completed_at = db.execute(
        select(func.now())
    ).scalar_one()

    db.flush()


def fail_turn_request(
    db: Session,
    *,
    turn: ConversationTurn,
    error_code: str,
) -> None:
    if turn.status == TURN_STATUS_FAILED:
        return

    if turn.status != TURN_STATUS_PROCESSING:
        raise TurnRequestStateError(
            "only processing turns can fail"
        )

    turn.status = TURN_STATUS_FAILED
    turn.error_code = (
        error_code.strip()[:120]
        if error_code
        else "turn_failed"
    )

    db.flush()
