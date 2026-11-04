"""Real SQLite integration tests for Bible Quiz AI quota accounting."""

from datetime import datetime

import pytest

from api.core.entitlements import ENTITLEMENT_BIBLE_QUIZZES_AI
from api.core.product_catalog import PLAN_CODE_PASTOR_PRO
from api.models.ai_usage_event import AIUsageEvent
from api.models.ai_usage_reservation import AIUsageReservation
from api.models.usage_bucket import UsageBucket
from api.services.ai_usage_metering import (
    UsageLimitExceeded,
    UsageReservationConflict,
    UsageReservationStateError,
)
from api.services.xyniva_usage_service import (
    complete_xyniva_usage,
    release_xyniva_usage,
    reserve_xyniva_usage,
)

from tests.test_church_bible_quiz_subscription_access import (
    add_membership,
    make_church,
    make_user,
    subscribe,
)

NOW = datetime(2026, 10, 24, 12, 0, 0)
KEY = ENTITLEMENT_BIBLE_QUIZZES_AI
METRIC = "bible_quiz_generation"


@pytest.fixture()
def db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.pool import StaticPool

    from api.db.database import Base
    from api.models.user import User
    from api.models.church import Church
    from api.models.church_membership import ChurchMembership
    from api.models.plan import Plan
    from api.models.plan_entitlement import PlanEntitlement
    from api.models.subscription import Subscription
    from api.services.product_catalog_sync import sync_product_catalog

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


def reserve(db, user, request_id, *, church_id=None, now=NOW):
    result = reserve_xyniva_usage(
        db,
        user=user,
        request_id=request_id,
        entitlement_key=KEY,
        metric=METRIC,
        units=1,
        church_id=church_id,
        now=now,
    )
    db.commit()
    return result


def complete(db, request_id, *, now=NOW):
    result = complete_xyniva_usage(
        db,
        request_id=request_id,
        now=now,
    )
    db.commit()
    return result


def release(db, request_id, *, now=NOW):
    result = release_xyniva_usage(
        db,
        request_id=request_id,
        now=now,
    )
    db.commit()
    return result


def test_free_pastor_ten_successes_exhaust_allowance(db):
    pastor = make_user(db, "Metered Free Pastor")

    for number in range(10):
        request_id = f"free-quiz-{number}"
        reserve(db, pastor, request_id)
        complete(db, request_id)

    bucket = db.query(UsageBucket).one()

    assert bucket.user_id == pastor.id
    assert bucket.church_id is None
    assert bucket.allowance_units == 10
    assert bucket.consumed_units == 10
    assert bucket.reserved_units == 0
    assert db.query(AIUsageEvent).count() == 10

    with pytest.raises(UsageLimitExceeded):
        reserve(db, pastor, "free-quiz-11")

    db.rollback()


def test_pending_reservations_also_count_against_limit(db):
    pastor = make_user(db, "Pending Pastor")

    for number in range(10):
        reserve(db, pastor, f"pending-{number}")

    bucket = db.query(UsageBucket).one()

    assert bucket.consumed_units == 0
    assert bucket.reserved_units == 10

    with pytest.raises(UsageLimitExceeded):
        reserve(db, pastor, "pending-11")

    db.rollback()


def test_failed_generation_releases_quota(db):
    pastor = make_user(db, "Failed Generation Pastor")

    reserve(db, pastor, "failed-quiz")
    release(db, "failed-quiz")

    bucket = db.query(UsageBucket).one()

    assert bucket.consumed_units == 0
    assert bucket.reserved_units == 0
    assert db.query(AIUsageEvent).count() == 0

    reserve(db, pastor, "replacement-quiz")
    complete(db, "replacement-quiz")

    assert bucket.consumed_units == 1


def test_duplicate_completion_is_not_double_charged(db):
    pastor = make_user(db, "Duplicate Pastor")

    reserve(db, pastor, "duplicate-quiz")
    complete(db, "duplicate-quiz")
    complete(db, "duplicate-quiz")

    bucket = db.query(UsageBucket).one()

    assert bucket.consumed_units == 1
    assert db.query(AIUsageEvent).count() == 1


def test_reusing_request_id_for_other_user_is_rejected(db):
    first = make_user(db, "First Request Owner")
    second = make_user(db, "Second Request Owner")

    reserve(db, first, "shared-request-id")

    with pytest.raises(UsageReservationConflict):
        reserve(db, second, "shared-request-id")

    db.rollback()


def test_consumed_generation_cannot_be_released(db):
    pastor = make_user(db, "Consumed Pastor")

    reserve(db, pastor, "consumed-quiz")
    complete(db, "consumed-quiz")

    with pytest.raises(UsageReservationStateError):
        release(db, "consumed-quiz")

    db.rollback()


def test_pastor_pro_one_hundred_monthly_generations(db):
    pastor = make_user(db, "Metered Pro Pastor")
    subscribe(db, PLAN_CODE_PASTOR_PRO, user=pastor)

    reserve(db, pastor, "pro-quiz-1")
    complete(db, "pro-quiz-1")

    bucket = db.query(UsageBucket).one()

    assert bucket.user_id == pastor.id
    assert bucket.allowance_units == 100
    assert bucket.consumed_units == 1


def test_two_churches_share_one_free_pastor_bucket(db):
    pastor = make_user(db, "Metered Multi Church Pastor")

    first = make_church(db, "Metered Church One", pastor)
    second = make_church(db, "Metered Church Two", pastor)

    add_membership(db, pastor, first)
    add_membership(db, pastor, second)

    for number in range(5):
        request_id = f"church-one-{number}"
        reserve(db, pastor, request_id, church_id=first.id)
        complete(db, request_id)

    for number in range(5):
        request_id = f"church-two-{number}"
        reserve(db, pastor, request_id, church_id=second.id)
        complete(db, request_id)

    buckets = db.query(UsageBucket).all()

    assert len(buckets) == 1
    assert buckets[0].user_id == pastor.id
    assert buckets[0].consumed_units == 10

    with pytest.raises(UsageLimitExceeded):
        reserve(
            db,
            pastor,
            "extra-church-quiz",
            church_id=second.id,
        )

    db.rollback()


def test_new_calendar_month_creates_new_baseline_bucket(db):
    pastor = make_user(db, "Monthly Reset Pastor")

    october = datetime(2026, 10, 24, 12, 0, 0)
    november = datetime(2026, 11, 1, 12, 0, 0)

    reserve(db, pastor, "october-quiz", now=october)
    complete(db, "october-quiz", now=october)

    reserve(db, pastor, "november-quiz", now=november)
    complete(db, "november-quiz", now=november)

    buckets = (
        db.query(UsageBucket)
        .order_by(UsageBucket.period_start)
        .all()
    )

    assert len(buckets) == 2
    assert buckets[0].period_start == datetime(2026, 10, 1)
    assert buckets[1].period_start == datetime(2026, 11, 1)
    assert all(bucket.consumed_units == 1 for bucket in buckets)
