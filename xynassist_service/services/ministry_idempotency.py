"""
Durable idempotency and recovery for ministry executions.

The processing claim is committed before external AI work. Processing
leases fence abandoned workers while allowing expired work to recover.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from xynassist_service.models.ministry_execution import (
    MinistryExecution,
)


MINISTRY_STATUS_PROCESSING = "processing"
MINISTRY_STATUS_COMPLETED = "completed"
MINISTRY_STATUS_FAILED = "failed"

MINISTRY_LEASE_SECONDS = 120


class MinistryRequestConflict(Exception):
    pass


class MinistryRequestInProgress(Exception):
    pass


class MinistryRequestStateError(Exception):
    pass


class MinistryLeaseLost(Exception):
    pass


@dataclass(frozen=True)
class MinistryClaim:
    execution: MinistryExecution
    lease_token: str | None
    replay_result: dict[str, Any] | None = None

    @property
    def is_replay(self) -> bool:
        return self.replay_result is not None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _lease_expiry() -> datetime:
    return _utcnow() + timedelta(
        seconds=MINISTRY_LEASE_SECONDS
    )


def _normalize_request_id(request_id: str) -> str:
    try:
        return str(uuid.UUID(request_id))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError(
            "request_id must be a UUID"
        ) from exc


def build_ministry_fingerprint(
    *,
    skill: str,
    payload: dict[str, Any],
) -> str:
    if not isinstance(payload, dict):
        raise ValueError("payload must be an object")

    normalized = json.dumps(
        {
            "skill": skill,
            "input": payload,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()


def _lock_request(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    request_id: str,
) -> None:
    # PostgreSQL receives a transaction-scoped advisory lock.
    # SQLite test databases do not support advisory locking.
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return

    lock_material = (
        f"ministry:{product}:"
        f"{external_user_id}:{request_id}"
    )

    db.execute(
        func.pg_advisory_xact_lock(
            func.hashtextextended(lock_material, 0)
        ).select()
    )


def _load_execution(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    request_id: str,
) -> MinistryExecution | None:
    return (
        db.query(MinistryExecution)
        .filter(
            MinistryExecution.product == product,
            MinistryExecution.external_user_id
            == external_user_id,
            MinistryExecution.request_id == request_id,
        )
        .one_or_none()
    )


def _decode_result(
    execution: MinistryExecution,
) -> dict[str, Any]:
    if execution.result_json is None:
        raise MinistryRequestStateError(
            "Completed ministry execution has no result"
        )

    try:
        result = json.loads(execution.result_json)
    except (TypeError, ValueError) as exc:
        raise MinistryRequestStateError(
            "Persisted ministry result is invalid"
        ) from exc

    if not isinstance(result, dict):
        raise MinistryRequestStateError(
            "Persisted ministry result is invalid"
        )

    return result


def _lease_is_fresh(
    execution: MinistryExecution,
) -> bool:
    expires_at = execution.lease_expires_at

    if expires_at is None:
        return False

    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(
            tzinfo=timezone.utc
        )

    return expires_at > _utcnow()


def claim_ministry_request(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    request_id: str,
    skill: str,
    payload: dict[str, Any],
) -> MinistryClaim:
    product = product.strip()
    external_user_id = external_user_id.strip()
    skill = skill.strip()

    if not product:
        raise ValueError("product is required")

    if not external_user_id:
        raise ValueError(
            "external_user_id is required"
        )

    if not skill:
        raise ValueError("skill is required")

    normalized_request_id = _normalize_request_id(
        request_id
    )

    fingerprint = build_ministry_fingerprint(
        skill=skill,
        payload=payload,
    )

    _lock_request(
        db,
        product=product,
        external_user_id=external_user_id,
        request_id=normalized_request_id,
    )

    execution = _load_execution(
        db,
        product=product,
        external_user_id=external_user_id,
        request_id=normalized_request_id,
    )

    if execution is not None:
        if (
            execution.skill != skill
            or execution.request_fingerprint
            != fingerprint
        ):
            raise MinistryRequestConflict(
                "request_id was already used for "
                "different ministry input"
            )

        if (
            execution.status
            == MINISTRY_STATUS_COMPLETED
        ):
            return MinistryClaim(
                execution=execution,
                lease_token=None,
                replay_result=_decode_result(
                    execution
                ),
            )

        if (
            execution.status
            == MINISTRY_STATUS_FAILED
        ):
            raise MinistryRequestStateError(
                "Ministry execution previously failed"
            )

        if (
            execution.status
            != MINISTRY_STATUS_PROCESSING
        ):
            raise MinistryRequestStateError(
                "Ministry execution has invalid state"
            )

        if _lease_is_fresh(execution):
            raise MinistryRequestInProgress(
                "Ministry request is already processing"
            )

        lease_token = str(uuid.uuid4())
        execution.lease_token = lease_token
        execution.lease_expires_at = (
            _lease_expiry()
        )
        execution.attempt_count += 1
        execution.error_code = None

        db.flush()

        return MinistryClaim(
            execution=execution,
            lease_token=lease_token,
        )

    lease_token = str(uuid.uuid4())

    execution = MinistryExecution(
        product=product,
        external_user_id=external_user_id,
        request_id=normalized_request_id,
        skill=skill,
        request_fingerprint=fingerprint,
        status=MINISTRY_STATUS_PROCESSING,
        lease_token=lease_token,
        lease_expires_at=_lease_expiry(),
        attempt_count=1,
    )

    db.add(execution)
    db.flush()

    return MinistryClaim(
        execution=execution,
        lease_token=lease_token,
    )


def require_ministry_lease(
    db: Session,
    *,
    product: str,
    external_user_id: str,
    request_id: str,
    execution_id: str,
    lease_token: str | None,
) -> MinistryExecution:
    if not lease_token:
        raise MinistryLeaseLost(
            "processing lease token is required"
        )

    normalized_request_id = _normalize_request_id(
        request_id
    )

    _lock_request(
        db,
        product=product,
        external_user_id=external_user_id,
        request_id=normalized_request_id,
    )

    execution = _load_execution(
        db,
        product=product,
        external_user_id=external_user_id,
        request_id=normalized_request_id,
    )

    if (
        execution is None
        or execution.id != execution_id
    ):
        raise MinistryLeaseLost(
            "Ministry execution no longer exists"
        )

    if (
        execution.status
        != MINISTRY_STATUS_PROCESSING
    ):
        raise MinistryLeaseLost(
            "Ministry execution is no longer processing"
        )

    if execution.lease_token != lease_token:
        raise MinistryLeaseLost(
            "processing lease is no longer owned "
            "by this worker"
        )

    return execution


def complete_ministry_request(
    db: Session,
    *,
    execution: MinistryExecution,
    lease_token: str | None,
    result: dict[str, Any],
) -> None:
    if execution.lease_token != lease_token:
        raise MinistryLeaseLost(
            "processing lease is no longer owned "
            "by this worker"
        )

    if not isinstance(result, dict):
        raise ValueError("result must be an object")

    execution.status = MINISTRY_STATUS_COMPLETED
    execution.result_json = json.dumps(
        result,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    execution.error_code = None
    execution.lease_token = None
    execution.lease_expires_at = None
    execution.completed_at = func.now()

    db.flush()


def fail_ministry_request(
    db: Session,
    *,
    execution: MinistryExecution,
    lease_token: str | None,
    error_code: str,
) -> None:
    if execution.lease_token != lease_token:
        raise MinistryLeaseLost(
            "processing lease is no longer owned "
            "by this worker"
        )

    execution.status = MINISTRY_STATUS_FAILED
    execution.error_code = error_code
    execution.lease_token = None
    execution.lease_expires_at = None

    db.flush()
