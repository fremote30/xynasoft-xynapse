"""Isolated integration tests for Bible Quiz request identity."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db.database import Base
from api.models.ai_usage_event import AIUsageEvent
from api.models.ai_usage_reservation import AIUsageReservation
from api.models.bible_quiz_generation_request import (
    BibleQuizGenerationRequest,
)
from api.models.church import Church
from api.models.church_membership import ChurchMembership
from api.models.plan import Plan
from api.models.plan_entitlement import PlanEntitlement
from api.models.subscription import Subscription
from api.models.usage_bucket import UsageBucket
from api.models.user import User
from api.services.ai_usage_metering import UsageLimitExceeded
from api.services.bible_quiz_request_identity import (
    BibleQuizGenerationInputs,
)
from api.services.bible_quiz_request_reservation import (
    BibleQuizGenerationRequestConflict,
    reserve_bible_quiz_generation_request,
)
from api.services.product_catalog_sync import sync_product_catalog
from api.services.xyniva_usage_service import release_xyniva_usage
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
        ],
    )

    session = sessionmaker(bind=engine)()

    try:
        sync_product_catalog(session)
        session.commit()
        yield session
    finally:
        session.close()
        engine.dispose()


def setup_request(db):
    pastor = make_user(db, f"Quiz Pastor {uuid4().hex[:8]}")
    church = make_church(
        db,
        f"Quiz Church {uuid4().hex[:8]}",
        pastor,
    )
    inputs = BibleQuizGenerationInputs(
        church_id=church.id,
        creator_user_id=pastor.id,
        topic="David and Goliath",
        scripture="1 Samuel 17",
        difficulty="beginner",
        question_count=5,
    )
    return pastor, church, inputs


def reserve(db, pastor, inputs, request_id=None):
    return reserve_bible_quiz_generation_request(
        db,
        user=pastor,
        request_id=request_id or str(uuid4()),
        inputs=inputs,
    )


def test_request_and_quota_reservation_commit_together(db):
    pastor, church, inputs = setup_request(db)
    request = reserve(db, pastor, inputs)
    db.commit()

    saved = db.get(
        BibleQuizGenerationRequest,
        request.request_id,
    )
    usage = db.query(AIUsageReservation).one()

    assert saved.status == "pending"
    assert saved.church_id == church.id
    assert saved.creator_user_id == pastor.id
    assert usage.request_id == saved.request_id
    assert usage.status == "reserved"
    assert db.query(UsageBucket).one().reserved_units == 1


def test_identical_retry_does_not_reserve_twice(db):
    pastor, church, inputs = setup_request(db)
    request_id = str(uuid4())

    first = reserve(db, pastor, inputs, request_id)
    db.commit()

    second = reserve(db, pastor, inputs, request_id)
    db.commit()

    assert first.request_id == second.request_id
    assert db.query(BibleQuizGenerationRequest).count() == 1
    assert db.query(AIUsageReservation).count() == 1
    assert db.query(UsageBucket).one().reserved_units == 1


def test_changed_inputs_rejected(db):
    pastor, church, inputs = setup_request(db)
    request_id = str(uuid4())

    reserve(db, pastor, inputs, request_id)
    db.commit()

    changed = inputs.model_copy(
        update={"question_count": 10}
    )

    with pytest.raises(
        BibleQuizGenerationRequestConflict,
        match="different inputs",
    ):
        reserve(db, pastor, changed, request_id)

    db.rollback()


def test_other_pastor_rejected(db):
    pastor, church, inputs = setup_request(db)
    request_id = str(uuid4())

    reserve(db, pastor, inputs, request_id)
    db.commit()

    other = make_user(
        db,
        f"Other Quiz Pastor {uuid4().hex[:8]}",
    )

    changed = inputs.model_copy(
        update={"creator_user_id": other.id}
    )

    with pytest.raises(BibleQuizGenerationRequestConflict):
        reserve(db, other, changed, request_id)

    db.rollback()


def test_transaction_rollback_removes_identity_and_quota(db):
    pastor, church, inputs = setup_request(db)

    reserve(db, pastor, inputs)
    db.rollback()

    assert db.query(BibleQuizGenerationRequest).count() == 0
    assert db.query(AIUsageReservation).count() == 0
    assert db.query(UsageBucket).count() == 0


def test_exhausted_quota_creates_no_extra_identity(db):
    pastor, church, inputs = setup_request(db)

    for _ in range(10):
        reserve(db, pastor, inputs)
        db.commit()

    with pytest.raises(UsageLimitExceeded):
        reserve(db, pastor, inputs)

    db.rollback()

    assert db.query(BibleQuizGenerationRequest).count() == 10
    assert db.query(AIUsageReservation).count() == 10



def test_missing_quota_reservation_rejected(db):
    pastor, church, inputs = setup_request(db)
    request_id = str(uuid4())

    reserve(db, pastor, inputs, request_id)
    db.commit()

    usage = db.query(AIUsageReservation).filter_by(
        request_id=request_id
    ).one()

    db.delete(usage)
    db.commit()

    with pytest.raises(
        BibleQuizGenerationRequestConflict,
        match="no quota reservation",
    ):
        reserve(db, pastor, inputs, request_id)

    db.rollback()


def test_consumed_reservation_does_not_reserve_again(db):
    from api.services.xyniva_usage_service import (
        complete_xyniva_usage,
    )

    pastor, church, inputs = setup_request(db)
    request_id = str(uuid4())

    reserve(db, pastor, inputs, request_id)
    db.commit()

    complete_xyniva_usage(db, request_id=request_id)
    db.commit()

    existing = reserve(db, pastor, inputs, request_id)
    db.commit()

    assert existing.request_id == request_id
    assert db.query(AIUsageReservation).count() == 1

    bucket = db.query(UsageBucket).one()
    assert bucket.consumed_units == 1
    assert bucket.reserved_units == 0


def test_quota_reservation_owner_mismatch_rejected(db):
    pastor, church, inputs = setup_request(db)
    request_id = str(uuid4())

    reserve(db, pastor, inputs, request_id)
    db.commit()

    other = make_user(
        db,
        f"Different Quota Owner {uuid4().hex[:8]}",
    )

    usage = db.query(AIUsageReservation).filter_by(
        request_id=request_id
    ).one()

    usage.user_id = other.id
    db.commit()

    with pytest.raises(
        BibleQuizGenerationRequestConflict,
        match="identity mismatch",
    ):
        reserve(db, pastor, inputs, request_id)

    db.rollback()

def test_released_reservation_must_not_authorize_retry(db):
    pastor, church, inputs = setup_request(db)
    request_id = str(uuid4())

    reserve(db, pastor, inputs, request_id)
    db.commit()

    release_xyniva_usage(db, request_id=request_id)
    db.commit()

    # Security requirement: a released request cannot restart AI work.
    with pytest.raises(Exception):
        reserve(db, pastor, inputs, request_id)

    db.rollback()
