import uuid

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from xynassist_service.db.database import Base
from xynassist_service.models.action_execution import (
    ActionExecution,
)
from xynassist_service.models.memory import Memory
from xynassist_service.services.memory_actions import (
    MemoryActionConfirmationRequired,
    MemoryActionTargetNotFound,
    execute_memory_action,
)


@pytest.fixture()
def engine():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
    )

    Base.metadata.create_all(engine)

    return engine


def new_request_id() -> str:
    return str(uuid.uuid4())


def test_remember_creates_memory_and_execution(
    engine,
):
    request_id = new_request_id()

    with Session(engine) as db:
        result = execute_memory_action(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=request_id,
            action_name="memory.remember",
            arguments={
                "memory_type": "preference",
                "key": "sermon_length",
                "value": "25 minutes",
            },
        )
        db.commit()

    assert result["memory_type"] == "preference"
    assert result["key"] == "sermon_length"
    assert result["status"] == "active"

    with Session(engine) as db:
        memories = db.execute(
            select(Memory)
        ).scalars().all()

        executions = db.execute(
            select(ActionExecution)
        ).scalars().all()

    assert len(memories) == 1
    assert memories[0].value == "25 minutes"
    assert len(executions) == 1


def test_exact_remember_retry_replays(
    engine,
):
    request_id = new_request_id()
    arguments = {
        "memory_type": "preference",
        "key": "sermon_length",
        "value": "25 minutes",
    }

    with Session(engine) as db:
        first = execute_memory_action(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=request_id,
            action_name="memory.remember",
            arguments=arguments,
        )
        db.commit()

    with Session(engine) as db:
        second = execute_memory_action(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=request_id,
            action_name="memory.remember",
            arguments=arguments,
        )
        db.commit()

    assert second == first

    with Session(engine) as db:
        assert len(
            db.execute(
                select(Memory)
            ).scalars().all()
        ) == 1

        assert len(
            db.execute(
                select(ActionExecution)
            ).scalars().all()
        ) == 1


def test_forget_requires_trusted_confirmation(
    engine,
):
    with Session(engine) as db:
        execute_memory_action(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=new_request_id(),
            action_name="memory.remember",
            arguments={
                "memory_type": "preference",
                "key": "sermon_length",
                "value": "25 minutes",
            },
        )
        db.commit()

    forget_id = new_request_id()

    with Session(engine) as db:
        with pytest.raises(
            MemoryActionConfirmationRequired
        ):
            execute_memory_action(
                db,
                product="xynafaith",
                external_user_id="user-1",
                request_id=forget_id,
                action_name="memory.forget",
                arguments={
                    "memory_type": "preference",
                    "key": "sermon_length",
                },
                trusted_confirmed=False,
            )

        db.rollback()

    with Session(engine) as db:
        memory = db.execute(
            select(Memory).where(
                Memory.key == "sermon_length"
            )
        ).scalar_one()

        assert memory.status == "active"

        execution = db.execute(
            select(ActionExecution).where(
                ActionExecution.request_id
                == forget_id
            )
        ).scalar_one_or_none()

        assert execution is None


def test_confirmed_forget_deactivates_memory(
    engine,
):
    with Session(engine) as db:
        remember = execute_memory_action(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=new_request_id(),
            action_name="memory.remember",
            arguments={
                "memory_type": "preference",
                "key": "sermon_length",
                "value": "25 minutes",
            },
        )
        db.commit()

    forget_id = new_request_id()

    with Session(engine) as db:
        result = execute_memory_action(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=forget_id,
            action_name="memory.forget",
            arguments={
                "memory_type": "preference",
                "key": "sermon_length",
            },
            trusted_confirmed=True,
        )
        db.commit()

    assert result["memory_id"] == remember["memory_id"]
    assert result["status"] == "inactive"

    with Session(engine) as db:
        memory = db.execute(
            select(Memory).where(
                Memory.id == remember["memory_id"]
            )
        ).scalar_one()

        assert memory.status == "inactive"


def test_exact_forget_retry_replays_after_deactivation(
    engine,
):
    with Session(engine) as db:
        execute_memory_action(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=new_request_id(),
            action_name="memory.remember",
            arguments={
                "memory_type": "preference",
                "key": "sermon_length",
                "value": "25 minutes",
            },
        )
        db.commit()

    request_id = new_request_id()
    arguments = {
        "memory_type": "preference",
        "key": "sermon_length",
    }

    with Session(engine) as db:
        first = execute_memory_action(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=request_id,
            action_name="memory.forget",
            arguments=arguments,
            trusted_confirmed=True,
        )
        db.commit()

    with Session(engine) as db:
        replay = execute_memory_action(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=request_id,
            action_name="memory.forget",
            arguments=arguments,
            trusted_confirmed=False,
        )
        db.commit()

    assert replay == first


def test_forget_is_owner_scoped(
    engine,
):
    with Session(engine) as db:
        execute_memory_action(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=new_request_id(),
            action_name="memory.remember",
            arguments={
                "memory_type": "preference",
                "key": "sermon_length",
                "value": "25 minutes",
            },
        )
        db.commit()

    with Session(engine) as db:
        with pytest.raises(
            MemoryActionTargetNotFound
        ):
            execute_memory_action(
                db,
                product="xynafaith",
                external_user_id="user-2",
                request_id=new_request_id(),
                action_name="memory.forget",
                arguments={
                    "memory_type": "preference",
                    "key": "sermon_length",
                },
                trusted_confirmed=True,
            )

        db.rollback()


def test_memory_action_rolls_back_atomically(
    engine,
):
    request_id = new_request_id()

    with Session(engine) as db:
        execute_memory_action(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id=request_id,
            action_name="memory.remember",
            arguments={
                "memory_type": "user_fact",
                "key": "rollback_test",
                "value": "temporary",
            },
        )

        db.rollback()

    with Session(engine) as db:
        memory = db.execute(
            select(Memory).where(
                Memory.key == "rollback_test"
            )
        ).scalar_one_or_none()

        execution = db.execute(
            select(ActionExecution).where(
                ActionExecution.request_id
                == request_id
            )
        ).scalar_one_or_none()

    assert memory is None
    assert execution is None


def test_forget_missing_target_fails_without_execution(
    engine,
):
    request_id = new_request_id()

    with Session(engine) as db:
        with pytest.raises(
            MemoryActionTargetNotFound
        ):
            execute_memory_action(
                db,
                product="xynafaith",
                external_user_id="user-1",
                request_id=request_id,
                action_name="memory.forget",
                arguments={
                    "memory_type": "preference",
                    "key": "missing",
                },
                trusted_confirmed=True,
            )

        db.rollback()

    with Session(engine) as db:
        execution = db.execute(
            select(ActionExecution).where(
                ActionExecution.request_id
                == request_id
            )
        ).scalar_one_or_none()

    assert execution is None


@pytest.mark.parametrize(
    "action_name,arguments",
    [
        (
            "memory.remember",
            {
                "memory_type": "preference",
                "key": "x",
            },
        ),
        (
            "memory.remember",
            {
                "memory_type": "unsupported",
                "key": "x",
                "value": "y",
            },
        ),
        (
            "memory.forget",
            {
                "memory_type": "preference",
                "key": "x",
                "confirmed": True,
            },
        ),
        (
            "sermon.delete",
            {},
        ),
    ],
)
def test_invalid_memory_action_input_rejected(
    engine,
    action_name,
    arguments,
):
    with Session(engine) as db:
        with pytest.raises(ValueError):
            execute_memory_action(
                db,
                product="xynafaith",
                external_user_id="user-1",
                request_id=new_request_id(),
                action_name=action_name,
                arguments=arguments,
                trusted_confirmed=True,
            )

        db.rollback()
