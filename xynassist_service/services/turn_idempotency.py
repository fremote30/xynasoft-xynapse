"""
Durable idempotency and processing-lease primitives for XynAssist turns.

A request_id identifies one logical AI turn for one trusted product user.
Processing leases allow abandoned work to be recovered while fencing stale
workers from completing or failing a newer attempt.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
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

TURN_LEASE_SECONDS = 600


class TurnIdempotencyError(Exception):
    """Base error for turn idempotency."""


class TurnRequestConflict(TurnIdempotencyError):
    """A request_id was reused with different logical input."""


class TurnRequestInProgress(TurnIdempotencyError):
    """The same logical request is already being processed."""


class TurnRequestStateError(TurnIdempotencyError):
    """Persisted turn state is internally inconsistent."""


class TurnLeaseLost(TurnRequestStateError):
    """The worker no longer owns the processing lease."""


@dataclass(frozen=True)
class TurnClaim:
    turn: ConversationTurn
    replay_response: dict[str, Any] | None
    lease_token: str | None

    @property
    def is_replay(self) -> bool:
        return self.replay_response is not None


def build_request_fingerprint(
    *,
    conversation_id: str,
    content: str,
    context: dict[str, Any] | None,
) -> str:
    """Produce a stable SHA-256 fingerprint of the logical request."""

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
    """Stable signed 64-bit key for PostgreSQL advisory locking."""

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
    """Serialize claims for the same logical request on PostgreSQL."""

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


def load_turn_by_id(
    db: Session,
    *,
    turn_id: str,
) -> ConversationTurn:
    turn = db.execute(
        select(
            ConversationTurn
        ).where(
            ConversationTurn.id == turn_id
        )
    ).scalar_one_or_none()

    if turn is None:
        raise TurnRequestStateError(
            "Persisted turn no longer exists"
        )

    return turn


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


def _database_now(db: Session) -> datetime:
    """Return authoritative database time normalized to UTC."""

    value = db.execute(
        select(func.now())
    ).scalar_one()

    normalized = _normalize_datetime(value)

    if normalized is None:
        raise TurnRequestStateError(
            "database did not return a valid timestamp"
        )

    return normalized


def _normalize_datetime(
    value: datetime | None,
) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value.astimezone(
        timezone.utc
    )


def _new_lease(
    *,
    now: datetime,
) -> tuple[str, datetime]:
    return (
        str(uuid.uuid4()),
        now + timedelta(
            seconds=TURN_LEASE_SECONDS
        ),
    )


def _processing_lease_state(
    turn: ConversationTurn,
    *,
    now: datetime,
) -> str:
    """
    Classify processing lease metadata.

    Both fields absent means a legacy 0002 processing row.
    Exactly one field present is inconsistent and fails closed.
    """

    has_token = bool(turn.lease_token)
    has_expiry = (
        turn.lease_expires_at is not None
    )

    if not has_token and not has_expiry:
        return "abandoned"

    if has_token != has_expiry:
        raise TurnRequestStateError(
            "processing turn has inconsistent "
            "lease metadata"
        )

    expires_at = _normalize_datetime(
        turn.lease_expires_at
    )

    if expires_at is None:
        raise TurnRequestStateError(
            "processing turn has invalid lease expiry"
        )

    if expires_at > now:
        return "fresh"

    return "expired"


def _assert_lease_owner(
    *,
    turn: ConversationTurn,
    lease_token: str,
) -> None:
    if not lease_token:
        raise TurnLeaseLost(
            "processing lease token is required"
        )

    if turn.lease_token != lease_token:
        raise TurnLeaseLost(
            "processing lease is no longer owned "
            "by this worker"
        )


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

    A fresh processing lease rejects duplicate execution. An expired or
    legacy lease-less processing row is recovered under a new fencing token.
    Completed requests replay. Failed requests remain fail-closed.
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

    now = _database_now(db)

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
                lease_token=None,
            )

        if (
            existing.status
            == TURN_STATUS_PROCESSING
        ):
            lease_state = _processing_lease_state(
                existing,
                now=now,
            )

            if lease_state == "fresh":
                raise TurnRequestInProgress(
                    "turn request is already processing"
                )

            lease_token, lease_expires_at = (
                _new_lease(
                    now=now,
                )
            )

            existing.lease_token = lease_token
            existing.lease_expires_at = (
                lease_expires_at
            )
            existing.attempt_count = (
                int(existing.attempt_count or 1)
                + 1
            )
            existing.error_code = None

            db.flush()

            return TurnClaim(
                turn=existing,
                replay_response=None,
                lease_token=lease_token,
            )

        if existing.status == TURN_STATUS_FAILED:
            raise TurnRequestStateError(
                "turn request previously failed"
            )

        raise TurnRequestStateError(
            "turn request has unknown state"
        )

    lease_token, lease_expires_at = (
        _new_lease(
            now=now,
        )
    )

    turn = ConversationTurn(
        id=str(uuid.uuid4()),
        product=product,
        external_user_id=external_user_id,
        conversation_id=conversation_id,
        request_id=normalized_request_id,
        request_fingerprint=fingerprint,
        status=TURN_STATUS_PROCESSING,
        lease_token=lease_token,
        lease_expires_at=lease_expires_at,
        attempt_count=1,
    )

    db.add(turn)

    try:
        db.flush()
    except IntegrityError:
        # PostgreSQL callers are protected by the advisory lock.
        # This path protects other dialects and unexpected races.
        db.rollback()
        raise TurnRequestInProgress(
            "turn request was claimed concurrently"
        )

    return TurnClaim(
        turn=turn,
        replay_response=None,
        lease_token=lease_token,
    )


def require_turn_lease(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    request_id: str,
    turn_id: str,
    lease_token: str,
) -> ConversationTurn:
    """
    Serialize with claim/recovery and return the authoritative
    processing row only when this worker still owns its lease.

    The transaction-scoped advisory lock remains held until the
    caller commits or rolls back.
    """

    product = product.strip()
    external_user_id = external_user_id.strip()
    request_id = request_id.strip()
    turn_id = turn_id.strip()

    try:
        normalized_request_id = str(
            uuid.UUID(request_id)
        )
    except (ValueError, AttributeError) as exc:
        raise ValueError(
            "request_id must be a UUID"
        ) from exc

    _lock_request(
        db,
        product=product,
        external_user_id=external_user_id,
        request_id=normalized_request_id,
    )

    turn = _load_turn(
        db,
        product=product,
        external_user_id=external_user_id,
        request_id=normalized_request_id,
    )

    if turn is None or turn.id != turn_id:
        raise TurnRequestStateError(
            "Persisted turn no longer exists"
        )

    if turn.status != TURN_STATUS_PROCESSING:
        raise TurnRequestStateError(
            "turn is no longer processing"
        )

    _assert_lease_owner(
        turn=turn,
        lease_token=lease_token,
    )

    return turn


def complete_turn_request(
    db: Session,
    *,
    turn: ConversationTurn,
    lease_token: str,
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

    _assert_lease_owner(
        turn=turn,
        lease_token=lease_token,
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
    turn.lease_token = None
    turn.lease_expires_at = None

    db.flush()


def fail_turn_request(
    db: Session,
    *,
    turn: ConversationTurn,
    lease_token: str,
    error_code: str,
) -> None:
    if turn.status == TURN_STATUS_FAILED:
        return

    if turn.status != TURN_STATUS_PROCESSING:
        raise TurnRequestStateError(
            "only processing turns can fail"
        )

    _assert_lease_owner(
        turn=turn,
        lease_token=lease_token,
    )

    turn.status = TURN_STATUS_FAILED
    turn.error_code = (
        error_code.strip()[:120]
        if error_code
        else "turn_failed"
    )
    turn.lease_token = None
    turn.lease_expires_at = None

    db.flush()
