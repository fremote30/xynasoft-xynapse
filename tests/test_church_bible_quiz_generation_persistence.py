"""SQLite integration tests for AI Bible Quiz draft persistence."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db.database import Base
from api.models.bible_quiz import BibleQuiz, BibleQuizQuestion
from api.models.bible_quiz_generation_request import BibleQuizGenerationRequest
from api.models.ai_usage_event import AIUsageEvent
from api.models.ai_usage_reservation import AIUsageReservation
from api.models.usage_bucket import UsageBucket
from api.services.ai_usage_metering import UsageReservationStateError
from api.services.bible_quiz_request_reservation import (
    reserve_bible_quiz_generation_request,
    claim_bible_quiz_generation_request,
)
from api.services.bible_quiz_request_identity import (
    BibleQuizGenerationInputs,
)
from api.services.bible_quiz_generation_service import (
    GeneratedBibleQuiz,
    persist_generated_bible_quiz_draft,
)
from api.services.xyniva_usage_service import (
    release_xyniva_usage,
    reserve_xyniva_usage,
)

from tests.test_church_bible_quiz_ai_metering import (
    KEY,
    METRIC,
    NOW,
)
from tests.test_church_bible_quiz_subscription_access import (
    make_church,
    make_user,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    from api.models.user import User
    from api.models.church import Church
    from api.models.church_membership import ChurchMembership
    from api.models.plan import Plan
    from api.models.plan_entitlement import PlanEntitlement
    from api.models.subscription import Subscription
    from api.services.product_catalog_sync import sync_product_catalog

    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Church.__table__,
            ChurchMembership.__table__,
            Plan.__table__,
            PlanEntitlement.__table__,
            Subscription.__table__,
            UsageBucket.__table__,
            AIUsageReservation.__table__,
            AIUsageEvent.__table__,
            BibleQuizGenerationRequest.__table__,
            BibleQuiz.__table__,
            BibleQuizQuestion.__table__,
        ],
    )

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        sync_product_catalog(session)
        session.commit()
        yield session
    finally:
        session.close()
        engine.dispose()


def generated_quiz():
    return GeneratedBibleQuiz.model_validate(
        {
            "quiz": {
                "title": "The Life of David",
                "description": "An introductory Bible Quiz",
                "scripture": "1 Samuel 17",
                "difficulty": "beginner",
            },
            "questions": [
                {
                    "position": 1,
                    "question_text": "Who defeated Goliath?",
                    "option_a": "David",
                    "option_b": "Saul",
                    "option_c": "Samuel",
                    "option_d": "Jonathan",
                    "correct_option": "A",
                    "explanation": "David defeated Goliath.",
                }
            ],
        }
    )


def generation_inputs(pastor, church, **changes):
    values = {
        "church_id": church.id,
        "creator_user_id": pastor.id,
        "topic": "The Life of David",
        "scripture": "1 Samuel 17",
        "difficulty": "beginner",
        "question_count": 1,
    }
    values.update(changes)
    return BibleQuizGenerationInputs.model_validate(values)


def setup_reserved_request(db):
    pastor = make_user(db, f"Quiz Pastor {uuid4().hex[:8]}")
    church = make_church(db, f"Quiz Church {uuid4().hex[:8]}", pastor)

    request_id = str(uuid4())

    reserve_bible_quiz_generation_request(
        db,
        user=pastor,
        request_id=request_id,
        inputs=generation_inputs(pastor, church),
        now=NOW,
    )
    claim_bible_quiz_generation_request(
        db,
        request_id=request_id,
        user_id=pastor.id,
    )
    db.commit()

    return pastor, church, request_id


def test_successful_generation_saves_draft_and_consumes_quota(db):
    pastor, church, request_id = setup_reserved_request(db)

    quiz = persist_generated_bible_quiz_draft(
        db,
        church_id=church.id,
        creator_user_id=pastor.id,
        request_id=request_id,
        inputs=generation_inputs(pastor, church),
        generated=generated_quiz(),
    )
    db.commit()

    assert quiz.status == "draft"
    assert quiz.generation_request_id == request_id

    questions = (
        db.query(BibleQuizQuestion)
        .filter(BibleQuizQuestion.quiz_id == quiz.id)
        .all()
    )

    assert len(questions) == 1
    assert questions[0].correct_option == "A"

    bucket = db.query(UsageBucket).one()

    assert bucket.consumed_units == 1
    assert bucket.reserved_units == 0
    assert db.query(AIUsageEvent).count() == 1


def test_retry_does_not_create_duplicate_or_charge_again(db):
    pastor, church, request_id = setup_reserved_request(db)

    first = persist_generated_bible_quiz_draft(
        db,
        church_id=church.id,
        creator_user_id=pastor.id,
        request_id=request_id,
        inputs=generation_inputs(pastor, church),
        generated=generated_quiz(),
    )
    db.commit()

    second = persist_generated_bible_quiz_draft(
        db,
        church_id=church.id,
        creator_user_id=pastor.id,
        request_id=request_id,
        inputs=generation_inputs(pastor, church),
        generated=generated_quiz(),
    )
    db.commit()

    assert first.id == second.id
    assert db.query(BibleQuiz).count() == 1
    assert db.query(AIUsageEvent).count() == 1


def test_failed_quota_completion_rolls_back_draft(db):
    pastor, church, request_id = setup_reserved_request(db)

    release_xyniva_usage(
        db,
        request_id=request_id,
    )
    db.commit()

    with pytest.raises(ValueError, match="not reserved"):
        persist_generated_bible_quiz_draft(
            db,
            church_id=church.id,
            creator_user_id=pastor.id,
            request_id=request_id,
            inputs=generation_inputs(pastor, church),
            generated=generated_quiz(),
        )

    db.rollback()

    assert db.query(BibleQuiz).count() == 0
    assert db.query(BibleQuizQuestion).count() == 0
    assert db.query(AIUsageEvent).count() == 0


def test_changed_inputs_cannot_reuse_completed_request(db):
    pastor, church, request_id = setup_reserved_request(db)

    persist_generated_bible_quiz_draft(
        db,
        church_id=church.id,
        creator_user_id=pastor.id,
        request_id=request_id,
        inputs=generation_inputs(pastor, church),
        generated=generated_quiz(),
    )
    db.commit()

    with pytest.raises(ValueError, match="different inputs"):
        persist_generated_bible_quiz_draft(
            db,
            church_id=church.id,
            creator_user_id=pastor.id,
            request_id=request_id,
            inputs=generation_inputs(
                pastor,
                church,
                question_count=2,
            ),
            generated=generated_quiz(),
        )

    db.rollback()

    assert db.query(BibleQuiz).count() == 1
    assert db.query(AIUsageEvent).count() == 1


def test_other_creator_cannot_reuse_completed_request(db):
    pastor, church, request_id = setup_reserved_request(db)

    persist_generated_bible_quiz_draft(
        db,
        church_id=church.id,
        creator_user_id=pastor.id,
        request_id=request_id,
        inputs=generation_inputs(pastor, church),
        generated=generated_quiz(),
    )
    db.commit()

    other = make_user(db, f"Other Pastor {uuid4().hex[:8]}")

    with pytest.raises(ValueError, match="another owner"):
        persist_generated_bible_quiz_draft(
            db,
            church_id=church.id,
            creator_user_id=other.id,
            request_id=request_id,
            inputs=generation_inputs(other, church),
            generated=generated_quiz(),
        )

    db.rollback()


def test_inputs_must_match_persistence_owner(db):
    pastor, church, request_id = setup_reserved_request(db)

    with pytest.raises(ValueError, match="request owner"):
        persist_generated_bible_quiz_draft(
            db,
            church_id=church.id,
            creator_user_id=pastor.id,
            request_id=request_id,
            inputs=generation_inputs(
                pastor,
                church,
                church_id=church.id + 999,
            ),
            generated=generated_quiz(),
        )

    db.rollback()
    assert db.query(BibleQuiz).count() == 0


def test_nonsequential_generated_questions_rejected(db):
    payload = generated_quiz().model_dump()
    payload["questions"][0]["position"] = 2

    with pytest.raises(ValueError, match="sequential"):
        GeneratedBibleQuiz.model_validate(payload)


def test_definitive_failure_releases_quota(db):
    from api.services.bible_quiz_request_reservation import (
        fail_bible_quiz_generation_request,
    )

    pastor, church, request_id = setup_reserved_request(db)

    request = fail_bible_quiz_generation_request(
        db,
        request_id=request_id,
        user_id=pastor.id,
    )

    from api.models.ai_usage_reservation import AIUsageReservation

    usage = db.query(AIUsageReservation).filter_by(
        request_id=request_id
    ).one()

    assert request.status == "failed"
    assert usage.status == "released"


def test_completed_request_cannot_be_failed(db):
    from api.services.bible_quiz_request_reservation import (
        fail_bible_quiz_generation_request,
        BibleQuizGenerationRequestConflict,
    )

    pastor, church, request_id = setup_reserved_request(db)

    persist_generated_bible_quiz_draft(
        db,
        church_id=church.id,
        creator_user_id=pastor.id,
        request_id=request_id,
        inputs=generation_inputs(pastor, church),
        generated=generated_quiz(),
    )

    with pytest.raises(BibleQuizGenerationRequestConflict):
        fail_bible_quiz_generation_request(
            db,
            request_id=request_id,
            user_id=pastor.id,
        )


def test_uncertain_request_retains_quota(db):
    from api.services.bible_quiz_request_reservation import (
        mark_bible_quiz_generation_uncertain,
    )
    from api.models.ai_usage_reservation import AIUsageReservation

    pastor, church, request_id = setup_reserved_request(db)

    request = mark_bible_quiz_generation_uncertain(
        db,
        request_id=request_id,
        user_id=pastor.id,
    )

    usage = db.query(AIUsageReservation).filter_by(
        request_id=request_id
    ).one()

    assert request.status == "uncertain"
    assert usage.status == "reserved"


def test_generation_request_cannot_be_claimed_twice(db):
    from api.services.bible_quiz_request_reservation import (
        claim_bible_quiz_generation_request,
        BibleQuizGenerationRequestConflict,
    )

    pastor, church, request_id = setup_reserved_request(db)

    with pytest.raises(BibleQuizGenerationRequestConflict):
        claim_bible_quiz_generation_request(
            db,
            request_id=request_id,
            user_id=pastor.id,
        )
