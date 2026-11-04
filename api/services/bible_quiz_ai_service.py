"""Safe XynAssist orchestration for AI Bible Quiz generation."""

from __future__ import annotations

from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from api.models.bible_quiz import BibleQuiz
from api.models.user import User
from api.services.bible_quiz_generation_service import (
    GeneratedBibleQuiz,
    persist_generated_bible_quiz_draft,
)
from api.services.bible_quiz_ai_validation import (
    validate_generated_bible_quiz,
)
from api.services.bible_quiz_ai_recovery import (
    recover_bible_quiz_for_user,
)
from api.services.bible_quiz_request_identity import (
    BibleQuizGenerationInputs,
)
from api.services.bible_quiz_request_reservation import (
    reserve_bible_quiz_generation_request,
    claim_bible_quiz_generation_request,
    mark_bible_quiz_generation_uncertain,
)
from api.services.xynassist_client import (
    XynAssistClient,
    XynAssistConfigurationError,
    XynAssistError,
)


class BibleQuizAIExecutionUncertain(RuntimeError):
    """Remote outcome is unknown; reservation must be retained."""


def _response(db, request):
    quiz = (
        db.query(BibleQuiz)
        .filter(
            BibleQuiz.generation_request_id == request.request_id
        )
        .one_or_none()
    )

    return {
        "request_id": request.request_id,
        "status": request.status,
        "quiz_id": quiz.id if quiz is not None else None,
    }


async def generate_bible_quiz_for_user(
    db: Session,
    *,
    user: User,
    inputs: BibleQuizGenerationInputs,
    request_id: str,
    client: XynAssistClient | None = None,
) -> dict:
    """Execute a new request once; never replay an existing execution."""

    normalized_id = str(UUID(request_id))

    try:
        request = reserve_bible_quiz_generation_request(
            db,
            user=user,
            request_id=normalized_id,
            inputs=inputs,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    if request.status in {"running", "uncertain"}:
        return await recover_bible_quiz_for_user(
            db,
            user=user,
            inputs=inputs,
            request_id=normalized_id,
            client=client,
        )

    if request.status != "pending":
        return _response(db, request)

    try:
        claim_bible_quiz_generation_request(
            db,
            request_id=normalized_id,
            user_id=user.id,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    xynassist = client or XynAssistClient()

    try:
        result = await xynassist.execute_ministry_skill(
            external_user_id=str(user.id),
            request_id=normalized_id,
            skill="bible_quiz.generate",
            payload={
                "topic": inputs.topic,
                "scripture": inputs.scripture,
                "difficulty": inputs.difficulty,
                "question_count": inputs.question_count,
            },
        )
        generated = validate_generated_bible_quiz(
            GeneratedBibleQuiz.model_validate(result),
            inputs,
        )

    except (XynAssistError, ValidationError, ValueError) as exc:
        db.rollback()

        try:
            mark_bible_quiz_generation_uncertain(
                db,
                request_id=normalized_id,
                user_id=user.id,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        raise BibleQuizAIExecutionUncertain(
            "Bible Quiz AI execution requires reconciliation"
        ) from exc

    try:
        quiz = persist_generated_bible_quiz_draft(
            db,
            church_id=inputs.church_id,
            creator_user_id=user.id,
            request_id=normalized_id,
            inputs=inputs,
            generated=generated,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "request_id": normalized_id,
        "status": "completed",
        "quiz_id": quiz.id,
    }
