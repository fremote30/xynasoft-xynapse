"""Reconcile AI Bible Quiz execution without replaying generation."""

from __future__ import annotations

from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from api.models.bible_quiz import BibleQuiz
from api.models.bible_quiz_generation_request import BibleQuizGenerationRequest
from api.models.user import User
from api.services.bible_quiz_ai_validation import validate_generated_bible_quiz
from api.services.bible_quiz_generation_service import (
    GeneratedBibleQuiz,
    persist_generated_bible_quiz_draft,
)
from api.services.bible_quiz_request_identity import (
    BibleQuizGenerationInputs,
    generation_input_fingerprint,
)
from api.services.bible_quiz_request_reservation import (
    BibleQuizGenerationRequestConflict,
    mark_bible_quiz_generation_uncertain,
)
from api.services.xynassist_client import XynAssistClient, XynAssistError


class BibleQuizAIRecoveryError(RuntimeError):
    """The remote outcome cannot yet be safely reconciled."""


async def recover_bible_quiz_for_user(
    db: Session,
    *,
    user: User,
    inputs: BibleQuizGenerationInputs,
    request_id: str,
    client: XynAssistClient | None = None,
) -> dict:
    normalized = str(UUID(request_id))
    request = db.get(BibleQuizGenerationRequest, normalized)

    if (
        request is None
        or request.creator_user_id != user.id
        or request.church_id != inputs.church_id
        or request.input_hash != generation_input_fingerprint(inputs)
    ):
        raise BibleQuizGenerationRequestConflict(
            "Generation request identity mismatch"
        )

    if request.status in {"completed", "failed", "pending"}:
        quiz = (
            db.query(BibleQuiz)
            .filter(BibleQuiz.generation_request_id == normalized)
            .one_or_none()
        )
        return {
            "request_id": normalized,
            "status": request.status,
            "quiz_id": quiz.id if quiz is not None else None,
        }

    if request.status not in {"running", "uncertain"}:
        raise BibleQuizAIRecoveryError("Unsupported local request status")

    xynassist = client or XynAssistClient()

    try:
        remote = await xynassist.get_ministry_execution_status(
            external_user_id=str(user.id),
            request_id=normalized,
        )
    except XynAssistError as exc:
        db.rollback()
        raise BibleQuizAIRecoveryError(
            "Remote execution status is unavailable"
        ) from exc

    if (
        remote.get("request_id") != normalized
        or remote.get("skill") != "bible_quiz.generate"
    ):
        raise BibleQuizAIRecoveryError(
            "Remote execution identity mismatch"
        )

    if remote.get("status") == "completed":
        try:
            generated = validate_generated_bible_quiz(
                GeneratedBibleQuiz.model_validate(remote["result"]),
                inputs,
            )
        except (ValidationError, ValueError) as exc:
            raise BibleQuizAIRecoveryError(
                "Recovered quiz failed validation"
            ) from exc

        try:
            quiz = persist_generated_bible_quiz_draft(
                db,
                church_id=inputs.church_id,
                creator_user_id=user.id,
                request_id=normalized,
                inputs=inputs,
                generated=generated,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        return {
            "request_id": normalized,
            "status": "completed",
            "quiz_id": quiz.id,
        }

    if remote.get("status") in {"in_progress", "uncertain", "failed"}:
        try:
            mark_bible_quiz_generation_uncertain(
                db,
                request_id=normalized,
                user_id=user.id,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        return {
            "request_id": normalized,
            "status": "uncertain",
            "quiz_id": None,
        }

    raise BibleQuizAIRecoveryError("Unsupported remote execution status")
