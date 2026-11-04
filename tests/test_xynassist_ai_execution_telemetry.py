from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from xynassist_service.db.database import Base
from xynassist_service.models.ai_execution import AIExecution
from xynassist_service.services.ai_execution_telemetry import (
    record_ai_execution,
)


def make_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine)

    Session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    return Session()


def test_records_provider_execution():
    db = make_session()

    execution = record_ai_execution(
        db,
        product="xynafaith",
        external_user_id="user-1",
        request_id="11111111-1111-4111-8111-111111111111",
        operation="sermon.generate",
        provider="fake",
        model="fake-ministry-v1",
        input_tokens=20,
        output_tokens=30,
        attempt_number=1,
    )

    db.commit()

    persisted = db.query(AIExecution).one()

    assert persisted.id == execution.id
    assert persisted.product == "xynafaith"
    assert persisted.external_user_id == "user-1"
    assert (
        persisted.request_id
        == "11111111-1111-4111-8111-111111111111"
    )
    assert persisted.operation == "sermon.generate"
    assert persisted.provider == "fake"
    assert persisted.model == "fake-ministry-v1"
    assert persisted.input_tokens == 20
    assert persisted.output_tokens == 30
    assert persisted.attempt_number == 1
    assert persisted.created_at is not None


def test_same_logical_request_can_record_multiple_executions():
    db = make_session()

    common = {
        "product": "xynafaith",
        "external_user_id": "user-1",
        "request_id": "22222222-2222-4222-8222-222222222222",
        "operation": "conversation.turn",
        "provider": "fake",
        "model": "fake-v1",
        "input_tokens": 10,
        "output_tokens": 15,
    }

    first = record_ai_execution(
        db,
        **common,
        attempt_number=1,
    )

    second = record_ai_execution(
        db,
        **common,
        attempt_number=2,
    )

    db.commit()

    rows = (
        db.query(AIExecution)
        .order_by(AIExecution.attempt_number)
        .all()
    )

    assert len(rows) == 2
    assert rows[0].id == first.id
    assert rows[1].id == second.id
    assert rows[0].request_id == rows[1].request_id
    assert rows[0].attempt_number == 1
    assert rows[1].attempt_number == 2


def test_token_counts_may_be_unknown():
    db = make_session()

    record_ai_execution(
        db,
        product="xynafaith",
        external_user_id="user-1",
        request_id="33333333-3333-4333-8333-333333333333",
        operation="sermon.generate",
        provider="fake",
        model="fake-v1",
        input_tokens=None,
        output_tokens=None,
    )

    db.commit()

    persisted = db.query(AIExecution).one()

    assert persisted.input_tokens is None
    assert persisted.output_tokens is None


def test_rejects_negative_tokens():
    db = make_session()

    try:
        record_ai_execution(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id="44444444-4444-4444-8444-444444444444",
            operation="sermon.generate",
            provider="fake",
            model="fake-v1",
            input_tokens=-1,
            output_tokens=10,
        )
    except ValueError as exc:
        assert "input_tokens" in str(exc)
    else:
        raise AssertionError("negative input tokens were accepted")


def test_rejects_invalid_attempt_number():
    db = make_session()

    try:
        record_ai_execution(
            db,
            product="xynafaith",
            external_user_id="user-1",
            request_id="55555555-5555-4555-8555-555555555555",
            operation="sermon.generate",
            provider="fake",
            model="fake-v1",
            input_tokens=1,
            output_tokens=1,
            attempt_number=0,
        )
    except ValueError as exc:
        assert "attempt_number" in str(exc)
    else:
        raise AssertionError("invalid attempt number was accepted")
