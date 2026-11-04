"""Validated persistence for AI-generated Bible Quiz drafts.

The caller owns the database transaction and commit.
This module does not invoke XynAssist or publish quizzes.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from api.models.bible_quiz import BibleQuiz, BibleQuizQuestion
from api.models.bible_quiz_generation_request import BibleQuizGenerationRequest
from api.models.ai_usage_reservation import AIUsageReservation
from api.core.entitlements import ENTITLEMENT_BIBLE_QUIZZES_AI
from api.services.ai_usage_metering import _acquire_request_lock
from api.schemas.bible_quiz_authoring import (
    BibleQuizCreate,
    BibleQuizQuestionCreate,
)
from api.services.bible_quiz_request_identity import (
    BibleQuizGenerationInputs,
    generation_input_fingerprint,
)
from api.services.xyniva_usage_service import complete_xyniva_usage


class GeneratedBibleQuiz(BaseModel):
    model_config = ConfigDict(extra="forbid")

    quiz: BibleQuizCreate
    questions: list[BibleQuizQuestionCreate] = Field(
        min_length=1,
        max_length=50,
    )

    @model_validator(mode="after")
    def validate_question_positions(self):
        positions = sorted(
            question.position for question in self.questions
        )

        expected = list(range(1, len(self.questions) + 1))

        if positions != expected:
            raise ValueError(
                "Generated quiz positions must be unique and sequential"
            )

        return self


def persist_generated_bible_quiz_draft(
    db: Session,
    *,
    church_id: int,
    creator_user_id: int,
    request_id: str,
    inputs: BibleQuizGenerationInputs,
    generated: GeneratedBibleQuiz,
) -> BibleQuiz:
    """Persist draft and complete quota in the caller's transaction.

    A previously saved request returns its existing draft.
    The caller must verify request ownership and input identity
    before invoking this function on a retry.
    """

    if (
        inputs.church_id != church_id
        or inputs.creator_user_id != creator_user_id
    ):
        raise ValueError(
            "Generation inputs do not match the request owner"
        )

    input_hash = generation_input_fingerprint(inputs)

    normalized_request_id = str(UUID(request_id))

    _acquire_request_lock(db, normalized_request_id)

    request = (
        db.query(BibleQuizGenerationRequest)
        .filter(
            BibleQuizGenerationRequest.request_id
            == normalized_request_id
        )
        .with_for_update()
        .one_or_none()
    )
    if request is None:
        raise ValueError("Durable generation request is required")
    if (
        request.church_id != church_id
        or request.creator_user_id != creator_user_id
    ):
        raise ValueError("Generation request belongs to another owner")

    if request.input_hash != input_hash:
        raise ValueError(
            "Generation request ID reused with different inputs"
        )

    usage = (
        db.query(AIUsageReservation)
        .filter(
            AIUsageReservation.request_id == normalized_request_id
        )
        .one_or_none()
    )
    if (
        usage is None
        or usage.user_id != creator_user_id
        or usage.entitlement_key != ENTITLEMENT_BIBLE_QUIZZES_AI
        or usage.metric != "bible_quiz_generation"
        or usage.units != 1
    ):
        raise ValueError("Generation quota identity mismatch")

    existing = (
        db.query(BibleQuiz)
        .filter(
            BibleQuiz.generation_request_id
            == normalized_request_id
        )
        .one_or_none()
    )

    if existing is not None:
        if (
            existing.church_id != church_id
            or existing.creator_user_id != creator_user_id
        ):
            raise ValueError(
                "Generation request belongs to another owner"
            )

        if existing.generation_input_hash != input_hash:
            raise ValueError(
                "Generation request ID reused with different inputs"
            )

        if request.status != "completed" or usage.status != "consumed":
            raise ValueError("Completed draft lifecycle mismatch")
        return existing

    if request.status not in {"running", "uncertain"}:
        raise ValueError("Generation request has not been claimed")
    if usage.status != "reserved":
        raise ValueError("Generation quota is not reserved")

    validated = GeneratedBibleQuiz.model_validate(generated)

    quiz = BibleQuiz(
        church_id=church_id,
        creator_user_id=creator_user_id,
        generation_request_id=normalized_request_id,
        generation_input_hash=input_hash,
        title=validated.quiz.title,
        description=validated.quiz.description,
        scripture=validated.quiz.scripture,
        difficulty=validated.quiz.difficulty,
        status="draft",
    )

    db.add(quiz)
    db.flush()

    for question in validated.questions:
        db.add(
            BibleQuizQuestion(
                quiz_id=quiz.id,
                **question.model_dump(),
            )
        )

    db.flush()

    complete_xyniva_usage(
        db,
        request_id=normalized_request_id,
    )

    request.status = "completed"
    db.flush()

    return quiz
