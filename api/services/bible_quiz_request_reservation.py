"""Durable, idempotent Bible Quiz AI request reservation."""

from uuid import UUID

from sqlalchemy.orm import Session

from api.core.entitlements import ENTITLEMENT_BIBLE_QUIZZES_AI
from api.models.ai_usage_reservation import AIUsageReservation
from api.services.ai_usage_metering import _acquire_request_lock
from api.models.bible_quiz_generation_request import (
    BibleQuizGenerationRequest,
)
from api.services.bible_quiz_request_identity import (
    BibleQuizGenerationInputs,
    generation_input_fingerprint,
)
from api.services.xyniva_usage_service import (
    reserve_xyniva_usage,
    release_xyniva_usage,
)


BIBLE_QUIZ_GENERATION_METRIC = "bible_quiz_generation"


class BibleQuizGenerationRequestConflict(ValueError):
    """A request ID was reused with a different identity or payload."""


def reserve_bible_quiz_generation_request(
    db: Session,
    *,
    user,
    request_id: str,
    inputs: BibleQuizGenerationInputs,
    now=None,
) -> BibleQuizGenerationRequest:
    """Reserve quota and persist request identity in one transaction.

    The caller owns commit and rollback. Commit before remote AI work.
    """

    normalized_request_id = str(UUID(request_id))

    if (
        inputs.creator_user_id != user.id
        or inputs.church_id <= 0
    ):
        raise BibleQuizGenerationRequestConflict(
            "Generation inputs do not match the authenticated user"
        )

    input_hash = generation_input_fingerprint(inputs)
    _acquire_request_lock(db, normalized_request_id)

    existing = (
        db.query(BibleQuizGenerationRequest)
        .filter(
            BibleQuizGenerationRequest.request_id
            == normalized_request_id
        )
        .one_or_none()
    )

    if existing is not None:
        if (
            existing.creator_user_id != user.id
            or existing.church_id != inputs.church_id
            or existing.input_hash != input_hash
        ):
            raise BibleQuizGenerationRequestConflict(
                "Generation request ID reused with different inputs"
            )

        usage = (
            db.query(AIUsageReservation)
            .filter(
                AIUsageReservation.request_id
                == normalized_request_id
            )
            .one_or_none()
        )

        if usage is None:
            raise BibleQuizGenerationRequestConflict(
                "Generation request has no quota reservation"
            )

        if (
            usage.user_id != user.id
            or usage.entitlement_key
            != ENTITLEMENT_BIBLE_QUIZZES_AI
            or usage.metric != BIBLE_QUIZ_GENERATION_METRIC
            or usage.units != 1
        ):
            raise BibleQuizGenerationRequestConflict(
                "Generation quota reservation identity mismatch"
            )

        if usage.status not in {"reserved", "consumed"}:
            raise BibleQuizGenerationRequestConflict(
                "Generation quota reservation is not reusable"
            )

        return existing

    reserve_xyniva_usage(
        db,
        user=user,
        request_id=normalized_request_id,
        entitlement_key=ENTITLEMENT_BIBLE_QUIZZES_AI,
        metric=BIBLE_QUIZ_GENERATION_METRIC,
        units=1,
        church_id=inputs.church_id,
        now=now,
    )

    request = BibleQuizGenerationRequest(
        request_id=normalized_request_id,
        church_id=inputs.church_id,
        creator_user_id=user.id,
        input_hash=input_hash,
        status="pending",
    )

    db.add(request)
    db.flush()

    return request

def claim_bible_quiz_generation_request(db, *, request_id, user_id):
    """Claim one pending request before remote AI execution.

    Caller commits the claim before calling XynAssist.
    """
    normalized = str(UUID(request_id))
    _acquire_request_lock(db, normalized)
    request = (
        db.query(BibleQuizGenerationRequest)
        .filter(BibleQuizGenerationRequest.request_id == normalized)
        .with_for_update()
        .one_or_none()
    )
    if request is None or request.creator_user_id != user_id:
        raise BibleQuizGenerationRequestConflict(
            "Generation request not found for owner"
        )
    if request.status != "pending":
        raise BibleQuizGenerationRequestConflict(
            "Generation request cannot be claimed again"
        )
    usage = (
        db.query(AIUsageReservation)
        .filter(AIUsageReservation.request_id == normalized)
        .one_or_none()
    )
    if (
        usage is None
        or usage.user_id != user_id
        or usage.entitlement_key != ENTITLEMENT_BIBLE_QUIZZES_AI
        or usage.metric != BIBLE_QUIZ_GENERATION_METRIC
        or usage.units != 1
        or usage.status != "reserved"
    ):
        raise BibleQuizGenerationRequestConflict(
            "Valid reserved quota required before execution"
        )
    request.status = "running"
    db.flush()
    return request


def mark_bible_quiz_generation_uncertain(db, *, request_id, user_id):
    """Keep quota reserved when remote execution is uncertain."""
    normalized = str(UUID(request_id))
    _acquire_request_lock(db, normalized)
    request = (
        db.query(BibleQuizGenerationRequest)
        .filter(BibleQuizGenerationRequest.request_id == normalized)
        .with_for_update()
        .one_or_none()
    )
    if request is None or request.creator_user_id != user_id:
        raise BibleQuizGenerationRequestConflict(
            "Generation request not found for owner"
        )
    if request.status not in {"running", "uncertain"}:
        raise BibleQuizGenerationRequestConflict(
            "Only running requests can become uncertain"
        )
    request.status = "uncertain"
    db.flush()
    return request



def fail_bible_quiz_generation_request(
    db,
    *,
    request_id,
    user_id,
    now=None,
):
    """Release quota for a definitive failure.

    The caller owns the transaction. Do not use this operation
    for timeouts, connection loss, or uncertain remote outcomes.
    """
    normalized = str(UUID(request_id))
    _acquire_request_lock(db, normalized)

    request = (
        db.query(BibleQuizGenerationRequest)
        .filter(
            BibleQuizGenerationRequest.request_id == normalized
        )
        .with_for_update()
        .one_or_none()
    )

    if request is None or request.creator_user_id != user_id:
        raise BibleQuizGenerationRequestConflict(
            "Generation request not found for owner"
        )

    if request.status != "running":
        raise BibleQuizGenerationRequestConflict(
            "Only running requests can fail definitively"
        )

    usage = (
        db.query(AIUsageReservation)
        .filter(
            AIUsageReservation.request_id == normalized
        )
        .one_or_none()
    )

    if (
        usage is None
        or usage.user_id != user_id
        or usage.entitlement_key != ENTITLEMENT_BIBLE_QUIZZES_AI
        or usage.metric != BIBLE_QUIZ_GENERATION_METRIC
        or usage.units != 1
        or usage.status != "reserved"
    ):
        raise BibleQuizGenerationRequestConflict(
            "Valid reserved quota required before failure"
        )

    release_xyniva_usage(
        db,
        request_id=normalized,
        now=now,
    )

    request.status = "failed"
    db.flush()
    return request
