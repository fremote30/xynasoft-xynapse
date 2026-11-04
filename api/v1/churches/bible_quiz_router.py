"""
XynaFaith V2 Bible Quiz authoring API.

Authoring is church-scoped and entitlement-gated.
Correct answers must never be returned by member-facing endpoints.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.core.church_dependencies import require_church_permission_dependency
from api.core.church_rbac import (
    PERMISSION_CHURCH_VIEW,
    PERMISSION_CONTENT_CREATE,
    PERMISSION_CONTENT_MANAGE,
    ROLE_PERMISSIONS,
)
from api.core.dependencies import get_current_user
from api.core.entitlements import (
    ENTITLEMENT_BIBLE_QUIZZES,
    ENTITLEMENT_BIBLE_QUIZZES_AUTHOR,
)
from api.db.database import get_db
from api.models.bible_quiz import (
    BibleQuiz,
    BibleQuizQuestion,
    BibleQuizAttempt,
    BibleQuizAnswer,
)
from api.models.church_membership import ChurchMembership
from api.models.user import User
from api.schemas.bible_quiz_authoring import (
    BibleQuizCreate,
    BibleQuizQuestionCreate,
    BibleQuizQuestionUpdate,
)
from api.schemas.bible_quiz_submission import BibleQuizSubmission
from api.services.effective_access_service import has_entitlement



from api.core.entitlements import ENTITLEMENT_BIBLE_QUIZZES_AI
from api.schemas.bible_quiz_ai import (
    BibleQuizAIGenerateRequest,
    BibleQuizAIGenerationResponse,
)
from api.services.bible_quiz_request_identity import (
    BibleQuizGenerationInputs,
)
from api.services.bible_quiz_ai_service import (
    generate_bible_quiz_for_user,
    BibleQuizAIExecutionUncertain,
)
from api.services.bible_quiz_ai_recovery import (
    recover_bible_quiz_for_user,
    BibleQuizAIRecoveryError,
)
from api.services.bible_quiz_request_reservation import (
    BibleQuizGenerationRequestConflict,
)
from api.services.xynassist_client import XynAssistError

router = APIRouter(
    prefix="/{church_id}/bible-quizzes",
    tags=["Church Bible Quizzes"],
)

church_view_required = require_church_permission_dependency(
    PERMISSION_CHURCH_VIEW
)

content_create_required = require_church_permission_dependency(
    PERMISSION_CONTENT_CREATE
)

content_manage_required = require_church_permission_dependency(
    PERMISSION_CONTENT_MANAGE
)


def _has_content_manage(membership: ChurchMembership) -> bool:
    return PERMISSION_CONTENT_MANAGE in ROLE_PERMISSIONS.get(
        membership.role, frozenset()
    )


def _require_entitlement(
    db: Session,
    user: User,
    church_id: int,
    entitlement_key: str = ENTITLEMENT_BIBLE_QUIZZES,
) -> None:
    if not has_entitlement(
        db,
        user,
        entitlement_key,
        church_id=church_id,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bible Quizzes are not available for this account",
        )


def _get_quiz(
    db: Session,
    church_id: int,
    quiz_id: int,
) -> BibleQuiz:
    quiz = (
        db.query(BibleQuiz)
        .filter(
            BibleQuiz.id == quiz_id,
            BibleQuiz.church_id == church_id,
        )
        .one_or_none()
    )

    if quiz is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bible Quiz not found",
        )

    return quiz


def _require_draft_editor(
    quiz: BibleQuiz,
    membership: ChurchMembership,
    user: User,
) -> None:
    if quiz.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft Bible Quizzes can be edited",
        )

    if (
        quiz.creator_user_id != user.id
        and not _has_content_manage(membership)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permission to edit Bible Quiz",
        )


def _quiz_payload(quiz: BibleQuiz) -> dict:
    return {
        "id": quiz.id,
        "church_id": quiz.church_id,
        "creator_user_id": quiz.creator_user_id,
        "title": quiz.title,
        "description": quiz.description,
        "scripture": quiz.scripture,
        "difficulty": quiz.difficulty,
        "status": quiz.status,
        "created_at": quiz.created_at.isoformat(),
        "updated_at": quiz.updated_at.isoformat(),
    }


def _author_question_payload(question: BibleQuizQuestion) -> dict:
    # Author-only response: includes the answer key.
    # Never reuse for member-facing quiz delivery.
    return {
        "id": question.id,
        "quiz_id": question.quiz_id,
        "position": question.position,
        "question_text": question.question_text,
        "option_a": question.option_a,
        "option_b": question.option_b,
        "option_c": question.option_c,
        "option_d": question.option_d,
        "correct_option": question.correct_option,
        "explanation": question.explanation,
    }



def _ai_quiz_inputs(
    church_id: int,
    user: User,
    request: BibleQuizAIGenerateRequest,
):
    return BibleQuizGenerationInputs(
        church_id=church_id,
        creator_user_id=user.id,
        topic=request.topic,
        scripture=request.scripture,
        difficulty=request.difficulty,
        question_count=request.question_count,
    )


@router.post(
    "/ai/generate",
    response_model=BibleQuizAIGenerationResponse,
)
async def generate_ai_bible_quiz(
    church_id: int,
    request: BibleQuizAIGenerateRequest,
    _: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entitlement(
        db,
        current_user,
        church_id,
        ENTITLEMENT_BIBLE_QUIZZES_AI,
    )

    inputs = _ai_quiz_inputs(
        church_id,
        current_user,
        request,
    )

    try:
        return await generate_bible_quiz_for_user(
            db,
            user=current_user,
            inputs=inputs,
            request_id=str(request.request_id),
        )
    except BibleQuizGenerationRequestConflict as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="AI quiz request conflicts with existing request",
        ) from exc
    except (
        BibleQuizAIExecutionUncertain,
        BibleQuizAIRecoveryError,
        XynAssistError,
    ) as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="AI quiz execution requires reconciliation",
        ) from exc


@router.post(
    "/ai/recover",
    response_model=BibleQuizAIGenerationResponse,
)
async def recover_ai_bible_quiz(
    church_id: int,
    request: BibleQuizAIGenerateRequest,
    _: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entitlement(
        db,
        current_user,
        church_id,
        ENTITLEMENT_BIBLE_QUIZZES_AI,
    )

    inputs = _ai_quiz_inputs(
        church_id,
        current_user,
        request,
    )

    try:
        return await recover_bible_quiz_for_user(
            db,
            user=current_user,
            inputs=inputs,
            request_id=str(request.request_id),
        )
    except BibleQuizGenerationRequestConflict as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="AI quiz request identity mismatch",
        ) from exc
    except (
        BibleQuizAIRecoveryError,
        XynAssistError,
    ) as exc:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="AI quiz status cannot be verified",
        ) from exc


@router.post("", status_code=status.HTTP_201_CREATED)
def create_bible_quiz(
    church_id: int,
    request: BibleQuizCreate,
    _: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entitlement(
        db,
        current_user,
        church_id,
        ENTITLEMENT_BIBLE_QUIZZES_AUTHOR,
    )

    quiz = BibleQuiz(
        church_id=church_id,
        creator_user_id=current_user.id,
        title=request.title,
        description=request.description,
        scripture=request.scripture,
        difficulty=request.difficulty,
        status="draft",
    )

    db.add(quiz)
    db.commit()
    db.refresh(quiz)

    return _quiz_payload(quiz)



# Batch 24.85 — creator-scoped draft review.
# These endpoints are intentionally separate from member delivery.


def _require_quiz_creator(quiz, current_user):
    if quiz.creator_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bible Quiz draft not found",
        )


def _require_author_draft(quiz, current_user):
    _require_quiz_creator(quiz, current_user)

    if quiz.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft Bible Quizzes can be edited",
        )


@router.get("/my-drafts")
def list_my_bible_quiz_drafts(
    church_id: int,
    _: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entitlement(
        db,
        current_user,
        church_id,
        ENTITLEMENT_BIBLE_QUIZZES_AUTHOR,
    )

    quizzes = (
        db.query(BibleQuiz)
        .filter(
            BibleQuiz.church_id == church_id,
            BibleQuiz.creator_user_id == current_user.id,
            BibleQuiz.status == "draft",
        )
        .order_by(BibleQuiz.id.desc())
        .all()
    )

    return [_quiz_payload(quiz) for quiz in quizzes]


@router.get("/{quiz_id}/author-draft")
def get_my_bible_quiz_draft(
    church_id: int,
    quiz_id: int,
    _: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entitlement(
        db,
        current_user,
        church_id,
        ENTITLEMENT_BIBLE_QUIZZES_AUTHOR,
    )

    quiz = (
        db.query(BibleQuiz)
        .filter(
            BibleQuiz.id == quiz_id,
            BibleQuiz.church_id == church_id,
            BibleQuiz.creator_user_id == current_user.id,
            BibleQuiz.status == "draft",
        )
        .one_or_none()
    )

    if quiz is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bible Quiz draft not found",
        )

    result = _quiz_payload(quiz)
    result["questions"] = [
        _author_question_payload(question)
        for question in sorted(
            quiz.questions,
            key=lambda item: item.position,
        )
    ]

    return result


@router.patch("/{quiz_id}/questions/{question_id}")
def update_my_bible_quiz_question(
    church_id: int,
    quiz_id: int,
    question_id: int,
    request: BibleQuizQuestionUpdate,
    _: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entitlement(
        db,
        current_user,
        church_id,
        ENTITLEMENT_BIBLE_QUIZZES_AUTHOR,
    )

    quiz = (
        db.query(BibleQuiz)
        .filter(
            BibleQuiz.id == quiz_id,
            BibleQuiz.church_id == church_id,
            BibleQuiz.creator_user_id == current_user.id,
        )
        .with_for_update()
        .one_or_none()
    )

    if quiz is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bible Quiz draft not found",
        )

    _require_author_draft(quiz, current_user)

    question = (
        db.query(BibleQuizQuestion)
        .filter(
            BibleQuizQuestion.id == question_id,
            BibleQuizQuestion.quiz_id == quiz.id,
        )
        .one_or_none()
    )

    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bible Quiz question not found",
        )

    changes = request.model_dump(exclude_unset=True)

    if "position" in changes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Question reordering is not supported",
        )

    for field, value in changes.items():
        setattr(question, field, value)

    db.commit()
    db.refresh(question)

    return _author_question_payload(question)


@router.post(
    "/{quiz_id}/questions",
    status_code=status.HTTP_201_CREATED,
)
def add_bible_quiz_question(
    church_id: int,
    quiz_id: int,
    request: BibleQuizQuestionCreate,
    membership: ChurchMembership = Depends(content_create_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entitlement(
        db,
        current_user,
        church_id,
        ENTITLEMENT_BIBLE_QUIZZES_AUTHOR,
    )

    quiz = _get_quiz(db, church_id, quiz_id)
    _require_draft_editor(quiz, membership, current_user)

    existing = (
        db.query(BibleQuizQuestion)
        .filter(
            BibleQuizQuestion.quiz_id == quiz.id,
            BibleQuizQuestion.position == request.position,
        )
        .first()
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bible Quiz question position already exists",
        )

    question = BibleQuizQuestion(
        quiz_id=quiz.id,
        **request.model_dump(),
    )

    db.add(question)
    db.commit()
    db.refresh(question)

    return _author_question_payload(question)



def _validate_quiz_for_publish(quiz: BibleQuiz) -> None:
    questions = sorted(
        quiz.questions,
        key=lambda question: question.position,
    )

    if not questions:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bible Quiz must contain at least one question",
        )

    positions = [question.position for question in questions]

    if positions != list(range(1, len(questions) + 1)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bible Quiz question positions must be sequential",
        )

    for question in questions:
        required_text = [
            question.question_text,
            question.option_a,
            question.option_b,
            question.option_c,
            question.option_d,
        ]

        if any(not value or not value.strip() for value in required_text):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Question {question.position} is incomplete",
            )

        if question.correct_option not in {"A", "B", "C", "D"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Question {question.position} has no valid answer",
            )


@router.post("/{quiz_id}/publish")
def publish_bible_quiz(
    church_id: int,
    quiz_id: int,
    _: ChurchMembership = Depends(content_manage_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entitlement(
        db,
        current_user,
        church_id,
        ENTITLEMENT_BIBLE_QUIZZES_AUTHOR,
    )

    quiz = _get_quiz(db, church_id, quiz_id)

    if quiz.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only draft Bible Quizzes can be published",
        )

    _validate_quiz_for_publish(quiz)

    quiz.status = "published"
    quiz.published_at = datetime.now(timezone.utc).replace(tzinfo=None)

    db.commit()
    db.refresh(quiz)

    return _quiz_payload(quiz)


@router.post("/{quiz_id}/archive")
def archive_bible_quiz(
    church_id: int,
    quiz_id: int,
    _: ChurchMembership = Depends(content_manage_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entitlement(
        db,
        current_user,
        church_id,
        ENTITLEMENT_BIBLE_QUIZZES_AUTHOR,
    )

    quiz = _get_quiz(db, church_id, quiz_id)

    if quiz.status != "published":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only published Bible Quizzes can be archived",
        )

    quiz.status = "archived"

    db.commit()
    db.refresh(quiz)

    return _quiz_payload(quiz)



def _member_question_payload(question: BibleQuizQuestion) -> dict:
    return {
        "id": question.id,
        "position": question.position,
        "question_text": question.question_text,
        "option_a": question.option_a,
        "option_b": question.option_b,
        "option_c": question.option_c,
        "option_d": question.option_d,
    }


@router.get("")
def list_published_bible_quizzes(
    church_id: int,
    _: ChurchMembership = Depends(church_view_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entitlement(db, current_user, church_id)

    quizzes = (
        db.query(BibleQuiz)
        .filter(
            BibleQuiz.church_id == church_id,
            BibleQuiz.status == "published",
        )
        .order_by(BibleQuiz.id.desc())
        .all()
    )

    return [_quiz_payload(quiz) for quiz in quizzes]


@router.get("/my-attempts")
def list_my_bible_quiz_attempts(
    church_id: int,
    _: ChurchMembership = Depends(church_view_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entitlement(db, current_user, church_id)

    attempts = (
        db.query(BibleQuizAttempt)
        .join(BibleQuiz, BibleQuizAttempt.quiz_id == BibleQuiz.id)
        .filter(
            BibleQuiz.church_id == church_id,
            BibleQuizAttempt.user_id == current_user.id,
            BibleQuizAttempt.status == "submitted",
        )
        .order_by(BibleQuizAttempt.id.desc())
        .all()
    )

    return [
        _member_attempt_payload(attempt)
        for attempt in attempts
    ]


@router.get("/{quiz_id}")
def get_published_bible_quiz(
    church_id: int,
    quiz_id: int,
    _: ChurchMembership = Depends(church_view_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entitlement(db, current_user, church_id)

    quiz = _get_quiz(db, church_id, quiz_id)

    if quiz.status != "published":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bible Quiz not found",
        )

    result = _quiz_payload(quiz)
    result["questions"] = [
        _member_question_payload(question)
        for question in sorted(
            quiz.questions,
            key=lambda item: item.position,
        )
    ]

    return result



@router.post(
    "/{quiz_id}/submit",
    status_code=status.HTTP_201_CREATED,
)
def submit_bible_quiz(
    church_id: int,
    quiz_id: int,
    request: BibleQuizSubmission,
    _: ChurchMembership = Depends(church_view_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entitlement(db, current_user, church_id)

    quiz = _get_quiz(db, church_id, quiz_id)

    if quiz.status != "published":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bible Quiz not found",
        )

    questions = sorted(
        quiz.questions,
        key=lambda question: question.position,
    )

    expected_ids = {question.id for question in questions}
    submitted_ids = [
        answer.question_id for answer in request.answers
    ]

    if (
        len(submitted_ids) != len(expected_ids)
        or len(set(submitted_ids)) != len(submitted_ids)
        or set(submitted_ids) != expected_ids
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Submit exactly one answer for each quiz question",
        )

    answers_by_question = {
        answer.question_id: answer.selected_option
        for answer in request.answers
    }

    correct_count = sum(
        answers_by_question[question.id] == question.correct_option
        for question in questions
    )

    total = len(questions)
    score = (100 * correct_count + total // 2) // total

    attempt = BibleQuizAttempt(
        quiz_id=quiz.id,
        user_id=current_user.id,
        status="submitted",
        score=score,
        total_questions=total,
        correct_answers=correct_count,
        submitted_at=datetime.utcnow(),
    )

    for question in questions:
        selected = answers_by_question[question.id]

        attempt.answers.append(
            BibleQuizAnswer(
                question_id=question.id,
                selected_option=selected,
                is_correct=int(
                    selected == question.correct_option
                ),
            )
        )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return {
        "attempt_id": attempt.id,
        "quiz_id": quiz.id,
        "status": attempt.status,
        "score": attempt.score,
        "total_questions": attempt.total_questions,
        "correct_answers": attempt.correct_answers,
        "submitted_at": attempt.submitted_at.isoformat(),
    }



def _member_attempt_payload(attempt: BibleQuizAttempt) -> dict:
    return {
        "attempt_id": attempt.id,
        "quiz_id": attempt.quiz_id,
        "status": attempt.status,
        "score": attempt.score,
        "total_questions": attempt.total_questions,
        "correct_answers": attempt.correct_answers,
        "started_at": attempt.started_at.isoformat(),
        "submitted_at": (
            attempt.submitted_at.isoformat()
            if attempt.submitted_at is not None
            else None
        ),
    }


@router.get("/{quiz_id}/my-attempts")
def list_my_attempts_for_bible_quiz(
    church_id: int,
    quiz_id: int,
    _: ChurchMembership = Depends(church_view_required),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_entitlement(db, current_user, church_id)

    _get_quiz(db, church_id, quiz_id)

    attempts = (
        db.query(BibleQuizAttempt)
        .filter(
            BibleQuizAttempt.quiz_id == quiz_id,
            BibleQuizAttempt.user_id == current_user.id,
            BibleQuizAttempt.status == "submitted",
        )
        .order_by(BibleQuizAttempt.id.desc())
        .all()
    )

    return [
        _member_attempt_payload(attempt)
        for attempt in attempts
    ]
