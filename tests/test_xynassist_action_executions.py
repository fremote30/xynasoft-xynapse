import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from xynassist_service.db.database import Base
from xynassist_service.services.action_executions import (
    ActionExecutionConflict,
    begin_action_execution,
    build_action_fingerprint,
    complete_action_execution,
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

    SessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _arguments():
    return {
        "memory_type": "preference",
        "key": "sermon_length",
        "value": "20 minutes",
    }


def test_action_fingerprint_is_stable():
    first = build_action_fingerprint(
        action_name="memory.remember",
        arguments={
            "key": "sermon_length",
            "value": "20 minutes",
            "memory_type": "preference",
        },
    )

    second = build_action_fingerprint(
        action_name="memory.remember",
        arguments=_arguments(),
    )

    assert first == second


def test_new_action_has_no_replay(db):
    result = begin_action_execution(
        db,
        product="xynafaith",
        external_user_id="user-1",
        request_id=str(uuid.uuid4()),
        action_name="memory.remember",
        arguments=_arguments(),
    )

    assert result is None


def test_completed_action_replays_exact_result(db):
    request_id = str(uuid.uuid4())

    assert begin_action_execution(
        db,
        product="xynafaith",
        external_user_id="user-1",
        request_id=request_id,
        action_name="memory.remember",
        arguments=_arguments(),
    ) is None

    complete_action_execution(
        db,
        product="xynafaith",
        external_user_id="user-1",
        request_id=request_id,
        action_name="memory.remember",
        arguments=_arguments(),
        result={
            "memory_id": "memory-1",
            "status": "active",
        },
    )

    db.commit()

    replay = begin_action_execution(
        db,
        product="xynafaith",
        external_user_id="user-1",
        request_id=request_id,
        action_name="memory.remember",
        arguments=_arguments(),
    )

    assert replay == {
        "memory_id": "memory-1",
        "status": "active",
    }


def test_same_request_with_different_arguments_conflicts(
    db,
):
    request_id = str(uuid.uuid4())

    complete_action_execution(
        db,
        product="xynafaith",
        external_user_id="user-1",
        request_id=request_id,
        action_name="memory.remember",
        arguments=_arguments(),
        result={"status": "active"},
    )

    db.commit()

    changed = _arguments()
    changed["value"] = "45 minutes"

    with pytest.raises(ActionExecutionConflict):
        begin_action_execution(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=request_id,
            action_name="memory.remember",
            arguments=changed,
        )


def test_same_request_with_different_action_conflicts(
    db,
):
    request_id = str(uuid.uuid4())

    complete_action_execution(
        db,
        product="xynafaith",
        external_user_id="user-1",
        request_id=request_id,
        action_name="memory.remember",
        arguments=_arguments(),
        result={"status": "active"},
    )

    db.commit()

    with pytest.raises(ActionExecutionConflict):
        begin_action_execution(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=request_id,
            action_name="memory.forget",
            arguments={
                "memory_type": "preference",
                "key": "sermon_length",
            },
        )


def test_request_id_is_scoped_to_owner(db):
    request_id = str(uuid.uuid4())

    complete_action_execution(
        db,
        product="xynafaith",
        external_user_id="user-1",
        request_id=request_id,
        action_name="memory.remember",
        arguments=_arguments(),
        result={"status": "active"},
    )

    db.commit()

    result = begin_action_execution(
        db,
        product="xynafaith",
        external_user_id="user-2",
        request_id=request_id,
        action_name="memory.remember",
        arguments=_arguments(),
    )

    assert result is None


def test_invalid_request_id_is_rejected(db):
    with pytest.raises(ValueError):
        begin_action_execution(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id="not-a-uuid",
            action_name="memory.remember",
            arguments=_arguments(),
        )


def test_execution_record_rolls_back_with_caller_transaction(
    db,
):
    request_id = str(uuid.uuid4())

    complete_action_execution(
        db,
        product="xynafaith",
        external_user_id="user-rollback",
        request_id=request_id,
        action_name="memory.remember",
        arguments=_arguments(),
        result={"status": "active"},
    )

    db.rollback()

    result = begin_action_execution(
        db,
        product="xynafaith",
        external_user_id="user-rollback",
        request_id=request_id,
        action_name="memory.remember",
        arguments=_arguments(),
    )

    assert result is None


@pytest.mark.parametrize(
    (
        "product",
        "external_user_id",
        "action_name",
    ),
    [
        ("", "user-1", "memory.remember"),
        ("xynafaith", "", "memory.remember"),
        ("xynafaith", "user-1", ""),
    ],
)
def test_completion_rejects_blank_identity_fields(
    db,
    product,
    external_user_id,
    action_name,
):
    with pytest.raises(ValueError):
        complete_action_execution(
            db,
            product=product,
            external_user_id=external_user_id,
            request_id=str(uuid.uuid4()),
            action_name=action_name,
            arguments=_arguments(),
            result={"status": "active"},
        )


def test_completion_rejects_non_object_arguments(db):
    with pytest.raises(ValueError):
        complete_action_execution(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=str(uuid.uuid4()),
            action_name="memory.remember",
            arguments=None,
            result={"status": "active"},
        )


def test_completion_rejects_non_object_result(db):
    with pytest.raises(ValueError):
        complete_action_execution(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=str(uuid.uuid4()),
            action_name="memory.remember",
            arguments=_arguments(),
            result=None,
        )
