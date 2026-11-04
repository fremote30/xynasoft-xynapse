from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

os.environ.setdefault(
    "XYNASSIST_DATABASE_URL",
    "sqlite://",
)

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from xynassist_service.db.database import Base
from xynassist_service.services.ministry_idempotency import (
    MINISTRY_STATUS_COMPLETED,
    MINISTRY_STATUS_PROCESSING,
    MinistryLeaseLost,
    MinistryRequestConflict,
    MinistryRequestInProgress,
    build_ministry_fingerprint,
    claim_ministry_request,
    complete_ministry_request,
    require_ministry_lease,
)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = Session()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _claim(db, *, request_id=None, payload=None):
    return claim_ministry_request(
        db,
        product="xynafaith",
        external_user_id="user-1",
        request_id=request_id or str(uuid.uuid4()),
        skill="sermon.generate",
        payload=payload or {"input": "Grace"},
    )


def test_fingerprint_is_stable_for_input_key_order():
    first = build_ministry_fingerprint(
        skill="sermon.generate",
        payload={
            "input": "Grace",
            "audience": "Youth",
        },
    )

    second = build_ministry_fingerprint(
        skill="sermon.generate",
        payload={
            "audience": "Youth",
            "input": "Grace",
        },
    )

    assert first == second


def test_new_request_is_claimed(db):
    claim = _claim(db)

    assert claim.is_replay is False
    assert claim.lease_token
    assert (
        claim.execution.status
        == MINISTRY_STATUS_PROCESSING
    )
    assert claim.execution.attempt_count == 1


def test_fresh_processing_request_is_rejected(db):
    request_id = str(uuid.uuid4())

    _claim(db, request_id=request_id)
    db.commit()

    with pytest.raises(
        MinistryRequestInProgress
    ):
        _claim(db, request_id=request_id)


def test_completed_request_replays_exact_result(db):
    request_id = str(uuid.uuid4())

    claim = _claim(
        db,
        request_id=request_id,
    )
    db.commit()

    execution = require_ministry_lease(
        db,
        product="xynafaith",
        external_user_id="user-1",
        request_id=request_id,
        execution_id=claim.execution.id,
        lease_token=claim.lease_token,
    )

    complete_ministry_request(
        db,
        execution=execution,
        lease_token=claim.lease_token,
        result={
            "title": "Grace",
            "scripture": "Ephesians 2:8-9",
        },
    )
    db.commit()

    replay = _claim(
        db,
        request_id=request_id,
    )

    assert replay.is_replay is True
    assert replay.replay_result == {
        "scripture": "Ephesians 2:8-9",
        "title": "Grace",
    }
    assert (
        replay.execution.status
        == MINISTRY_STATUS_COMPLETED
    )


def test_same_request_with_changed_input_conflicts(db):
    request_id = str(uuid.uuid4())

    _claim(
        db,
        request_id=request_id,
        payload={"input": "Grace"},
    )
    db.commit()

    with pytest.raises(MinistryRequestConflict):
        _claim(
            db,
            request_id=request_id,
            payload={"input": "Faith"},
        )


def test_expired_processing_request_recovers(db):
    request_id = str(uuid.uuid4())

    first = _claim(
        db,
        request_id=request_id,
    )

    first.execution.lease_expires_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=1)
    )
    db.commit()

    recovered = _claim(
        db,
        request_id=request_id,
    )

    assert recovered.lease_token
    assert recovered.lease_token != first.lease_token
    assert recovered.execution.attempt_count == 2


def test_old_worker_is_fenced_after_recovery(db):
    request_id = str(uuid.uuid4())

    first = _claim(
        db,
        request_id=request_id,
    )
    old_token = first.lease_token
    execution_id = first.execution.id

    first.execution.lease_expires_at = (
        datetime.now(timezone.utc)
        - timedelta(seconds=1)
    )
    db.commit()

    recovered = _claim(
        db,
        request_id=request_id,
    )
    db.commit()

    assert recovered.lease_token != old_token

    with pytest.raises(MinistryLeaseLost):
        require_ministry_lease(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=request_id,
            execution_id=execution_id,
            lease_token=old_token,
        )


def test_invalid_request_id_fails_closed(db):
    with pytest.raises(
        ValueError,
        match="request_id must be a UUID",
    ):
        _claim(
            db,
            request_id="not-a-uuid",
        )
