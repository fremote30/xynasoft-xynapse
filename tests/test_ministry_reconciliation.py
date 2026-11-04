from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

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
    RESERVATION_RESERVED,
    RESERVATION_RELEASED,
    reserve_usage,
    release_usage,
)
from api.services.ministry_skill_metering import ministry_skill_access
from api.services.ministry_skill_service import (
    MinistryExecutionError,
    reconcile_ministry_for_user,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
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
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def user(db):
    row = User(
        name="Reconciliation User",
        email="reconciliation@example.test",
        password="test-only",
        role="member",
        is_verified=True,
    )
    db.add(row)
    db.commit()
    return row


def create_reservation(db, user, skill="sermon.generate"):
    request_id = str(uuid4())
    entitlement, metric = ministry_skill_access(skill)
    reservation = reserve_usage(
        db,
        request_id=request_id,
        actor_user_id=user.id,
        quota_user_id=user.id,
        quota_church_id=None,
        subscription_id=None,
        entitlement_key=entitlement,
        metric=metric,
        units=1,
        allowance_units=10,
        usage_period="monthly",
    )
    db.commit()
    return request_id, reservation


class FakeStatusClient:
    def __init__(self, status="completed", result=None, skill=None):
        self.status = status
        self.result = result
        self.skill = skill
        self.calls = []

    async def get_ministry_execution_status(
        self, *, external_user_id, request_id
    ):
        self.calls.append((external_user_id, request_id))
        return {
            "request_id": request_id,
            "skill": self.skill or "sermon.generate",
            "status": self.status,
            "result": (
                self.result
                if self.result is not None
                else (
                    {"title": "Test Sermon"}
                    if self.status == "completed"
                    else None
                )
            ),
            "error_code": None,
        }


@pytest.mark.anyio
async def test_completed_execution_consumes_exactly_once(db, user):
    request_id, reservation = create_reservation(db, user)
    client = FakeStatusClient()

    first = await reconcile_ministry_for_user(
        db, user=user, request_id=request_id, client=client
    )
    second = await reconcile_ministry_for_user(
        db, user=user, request_id=request_id, client=client
    )

    db.refresh(reservation)
    bucket = db.get(UsageBucket, reservation.bucket_id)

    assert first == second
    assert first["status"] == "completed"
    assert reservation.status == RESERVATION_CONSUMED
    assert bucket.consumed_units == 1
    assert bucket.reserved_units == 0
    assert db.query(AIUsageEvent).filter_by(
        request_id=request_id
    ).count() == 1
    assert client.calls == [
        (str(user.id), request_id),
        (str(user.id), request_id),
    ]


@pytest.mark.anyio
async def test_cross_user_cannot_reconcile(db, user):
    request_id, reservation = create_reservation(db, user)
    other = SimpleNamespace(id=user.id + 100)
    client = FakeStatusClient()

    with pytest.raises(MinistryExecutionError):
        await reconcile_ministry_for_user(
            db, user=other, request_id=request_id, client=client
        )

    db.refresh(reservation)
    assert reservation.status == RESERVATION_RESERVED
    assert client.calls == []


@pytest.mark.anyio
async def test_skill_mismatch_never_consumes(db, user):
    request_id, reservation = create_reservation(db, user)
    client = FakeStatusClient(skill="content.transform")

    with pytest.raises(MinistryExecutionError):
        await reconcile_ministry_for_user(
            db, user=user, request_id=request_id, client=client
        )

    db.refresh(reservation)
    assert reservation.status == RESERVATION_RESERVED


@pytest.mark.anyio
@pytest.mark.parametrize(
    "status", ["in_progress", "uncertain", "failed"]
)
async def test_unresolved_execution_keeps_reservation(
    db, user, status
):
    request_id, reservation = create_reservation(db, user)
    client = FakeStatusClient(status=status)

    result = await reconcile_ministry_for_user(
        db, user=user, request_id=request_id, client=client
    )

    db.refresh(reservation)
    assert result["status"] == status
    assert result["result"] is None
    assert reservation.status == RESERVATION_RESERVED


@pytest.mark.anyio
async def test_released_reservation_cannot_be_consumed(db, user):
    request_id, reservation = create_reservation(db, user)
    release_usage(db, request_id=request_id)
    db.commit()
    client = FakeStatusClient()

    with pytest.raises(MinistryExecutionError):
        await reconcile_ministry_for_user(
            db, user=user, request_id=request_id, client=client
        )

    db.refresh(reservation)
    assert reservation.status == RESERVATION_RELEASED
    assert client.calls == []


@pytest.mark.anyio
async def test_content_transform_reconciles(db, user):
    request_id, reservation = create_reservation(
        db, user, skill="content.transform"
    )
    client = FakeStatusClient(
        skill="content.transform",
        result={"outputs": {"social_post": "Faith and hope"}},
    )

    result = await reconcile_ministry_for_user(
        db, user=user, request_id=request_id, client=client
    )

    db.refresh(reservation)
    assert result["skill"] == "content.transform"
    assert result["status"] == "completed"
    assert reservation.status == RESERVATION_CONSUMED


@pytest.mark.anyio
async def test_malformed_remote_result_never_consumes(db, user):
    request_id, reservation = create_reservation(db, user)
    client = FakeStatusClient(result={})

    with pytest.raises(MinistryExecutionError):
        await reconcile_ministry_for_user(
            db, user=user, request_id=request_id, client=client
        )

    db.refresh(reservation)
    assert reservation.status == RESERVATION_RESERVED
    assert db.query(AIUsageEvent).count() == 0
