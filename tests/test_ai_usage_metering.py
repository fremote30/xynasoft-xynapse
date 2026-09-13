"""
XynaFaith V2 AI usage metering lifecycle tests.

These tests use an isolated SQLite database. They do not touch
the V1 or V2 PostgreSQL development databases.
"""

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db.database import Base
from api.models.ai_usage_event import AIUsageEvent
from api.models.ai_usage_reservation import AIUsageReservation
from api.models.church import Church
from api.models.plan import Plan
from api.models.subscription import Subscription
from api.models.usage_bucket import UsageBucket
from api.models.user import User
from api.services.ai_usage_metering import (
    RESERVATION_CONSUMED,
    RESERVATION_RELEASED,
    RESERVATION_RESERVED,
    UsageLimitExceeded,
    UsageReservationConflict,
    UsageReservationStateError,
    complete_usage,
    release_usage,
    reserve_usage,
    resolve_usage_period,
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
            Church.__table__,
            User.__table__,
            Plan.__table__,
            Subscription.__table__,
            UsageBucket.__table__,
            AIUsageReservation.__table__,
            AIUsageEvent.__table__,
        ],
    )

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def user(db):
    row = User(
        name="Metering User",
        email="metering-user@example.test",
        password="not-a-real-password",
        role="member",
        is_verified=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


NOW = datetime(2026, 9, 13, 12, 0, 0)


def reserve(
    db,
    user,
    *,
    request_id,
    units=1,
    allowance=3,
    metric="xyniva_turn",
    subscription_id=None,
):
    return reserve_usage(
        db,
        request_id=request_id,
        actor_user_id=user.id,
        quota_user_id=user.id,
        quota_church_id=None,
        subscription_id=subscription_id,
        entitlement_key="xyniva.chat",
        metric=metric,
        units=units,
        allowance_units=allowance,
        usage_period="monthly",
        now=NOW,
    )


def test_monthly_period_contract():
    period = resolve_usage_period(
        "monthly",
        now=NOW,
    )

    assert period.start == datetime(2026, 9, 1)
    assert period.end == datetime(2026, 10, 1)


def test_reserve_holds_bucket_quota(db, user):
    reservation = reserve(
        db,
        user,
        request_id="reserve-1",
    )
    db.commit()

    bucket = db.query(UsageBucket).one()

    assert reservation.status == RESERVATION_RESERVED
    assert bucket.reserved_units == 1
    assert bucket.consumed_units == 0


def test_complete_moves_reserved_to_consumed_and_writes_event(db, user):
    reserve(
        db,
        user,
        request_id="complete-1",
    )
    db.commit()

    reservation = complete_usage(
        db,
        request_id="complete-1",
        now=NOW,
    )
    db.commit()

    bucket = db.query(UsageBucket).one()
    events = db.query(AIUsageEvent).all()

    assert reservation.status == RESERVATION_CONSUMED
    assert bucket.reserved_units == 0
    assert bucket.consumed_units == 1

    assert len(events) == 1
    assert events[0].request_id == "complete-1"
    assert events[0].units == 1


def test_complete_is_idempotent(db, user):
    reserve(
        db,
        user,
        request_id="complete-idempotent",
    )
    db.commit()

    complete_usage(
        db,
        request_id="complete-idempotent",
        now=NOW,
    )
    db.commit()

    complete_usage(
        db,
        request_id="complete-idempotent",
        now=NOW,
    )
    db.commit()

    bucket = db.query(UsageBucket).one()

    assert bucket.reserved_units == 0
    assert bucket.consumed_units == 1
    assert db.query(AIUsageEvent).count() == 1


def test_release_returns_reserved_quota(db, user):
    reserve(
        db,
        user,
        request_id="release-1",
    )
    db.commit()

    reservation = release_usage(
        db,
        request_id="release-1",
        now=NOW,
    )
    db.commit()

    bucket = db.query(UsageBucket).one()

    assert reservation.status == RESERVATION_RELEASED
    assert bucket.reserved_units == 0
    assert bucket.consumed_units == 0
    assert db.query(AIUsageEvent).count() == 0


def test_release_is_idempotent(db, user):
    reserve(
        db,
        user,
        request_id="release-idempotent",
    )
    db.commit()

    release_usage(
        db,
        request_id="release-idempotent",
        now=NOW,
    )
    db.commit()

    release_usage(
        db,
        request_id="release-idempotent",
        now=NOW,
    )
    db.commit()

    bucket = db.query(UsageBucket).one()

    assert bucket.reserved_units == 0
    assert bucket.consumed_units == 0


def test_consumed_usage_cannot_be_released(db, user):
    reserve(
        db,
        user,
        request_id="consumed-no-release",
    )
    db.commit()

    complete_usage(
        db,
        request_id="consumed-no-release",
        now=NOW,
    )
    db.commit()

    with pytest.raises(UsageReservationStateError):
        release_usage(
            db,
            request_id="consumed-no-release",
            now=NOW,
        )


def test_released_usage_cannot_be_completed(db, user):
    reserve(
        db,
        user,
        request_id="released-no-complete",
    )
    db.commit()

    release_usage(
        db,
        request_id="released-no-complete",
        now=NOW,
    )
    db.commit()

    with pytest.raises(UsageReservationStateError):
        complete_usage(
            db,
            request_id="released-no-complete",
            now=NOW,
        )


def test_cap_blocks_new_reservation(db, user):
    reserve(
        db,
        user,
        request_id="cap-1",
        allowance=1,
    )
    db.commit()

    with pytest.raises(UsageLimitExceeded):
        reserve(
            db,
            user,
            request_id="cap-2",
            allowance=1,
        )

    db.rollback()

    assert db.query(AIUsageReservation).count() == 1

    bucket = db.query(UsageBucket).one()
    assert bucket.reserved_units == 1
    assert bucket.consumed_units == 0


def test_same_request_is_idempotent(db, user):
    first = reserve(
        db,
        user,
        request_id="same-request",
    )
    db.commit()

    second = reserve(
        db,
        user,
        request_id="same-request",
    )
    db.commit()

    assert first.id == second.id

    bucket = db.query(UsageBucket).one()

    assert bucket.reserved_units == 1
    assert db.query(AIUsageReservation).count() == 1


def test_same_request_different_metric_conflicts(db, user):
    reserve(
        db,
        user,
        request_id="request-conflict",
        metric="xyniva_turn",
    )
    db.commit()

    with pytest.raises(UsageReservationConflict):
        reserve(
            db,
            user,
            request_id="request-conflict",
            metric="sermon_generation",
        )


def test_same_request_different_subscription_conflicts(db, user):
    reserve(
        db,
        user,
        request_id="subscription-conflict",
        subscription_id=None,
    )
    db.commit()

    with pytest.raises(UsageReservationConflict):
        reserve(
            db,
            user,
            request_id="subscription-conflict",
            subscription_id=999,
        )


def test_completed_usage_counts_against_cap(db, user):
    reserve(
        db,
        user,
        request_id="completed-cap-1",
        allowance=1,
    )
    db.commit()

    complete_usage(
        db,
        request_id="completed-cap-1",
        now=NOW,
    )
    db.commit()

    with pytest.raises(UsageLimitExceeded):
        reserve(
            db,
            user,
            request_id="completed-cap-2",
            allowance=1,
        )

    db.rollback()

    bucket = db.query(UsageBucket).one()

    assert bucket.reserved_units == 0
    assert bucket.consumed_units == 1


def test_allowance_can_expand_mid_period(db, user):
    reserve(
        db,
        user,
        request_id="expand-1",
        allowance=1,
    )
    db.commit()

    second = reserve(
        db,
        user,
        request_id="expand-2",
        allowance=2,
    )
    db.commit()

    bucket = db.query(UsageBucket).one()

    assert second.status == RESERVATION_RESERVED
    assert bucket.allowance_units == 2
    assert bucket.reserved_units == 2


def test_allowance_does_not_shrink_mid_period(db, user):
    reserve(
        db,
        user,
        request_id="shrink-1",
        allowance=5,
    )
    db.commit()

    reserve(
        db,
        user,
        request_id="shrink-2",
        allowance=2,
    )
    db.commit()

    bucket = db.query(UsageBucket).one()

    assert bucket.allowance_units == 5
    assert bucket.reserved_units == 2
