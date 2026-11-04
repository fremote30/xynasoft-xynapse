from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from xynassist_service.db.database import Base
import xynassist_service.models  # noqa: F401
from xynassist_service.models.ai_cost_rate import AICostRate
from xynassist_service.models.ai_execution import AIExecution
from xynassist_service.services.ai_cost_rates import (
    AICostRateNotFound,
)
from xynassist_service.services.ai_execution_costs import (
    AIExecutionUsageMissing,
    _token_cost_micro_usd,
    calculate_ai_execution_cost,
)


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
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
        engine.dispose()


def add_rate(
    db,
    *,
    input_rate=1_000_000,
    output_rate=2_000_000,
):
    row = AICostRate(
        provider="openai",
        model="example-model",
        input_cost_per_million_micro_usd=input_rate,
        output_cost_per_million_micro_usd=output_rate,
        effective_from=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
    )

    db.add(row)
    db.flush()

    return row


def add_execution(
    db,
    *,
    input_tokens=500_000,
    output_tokens=250_000,
    model="example-model",
):
    row = AIExecution(
        product="xynafaith",
        external_user_id="user-1",
        request_id="11111111-1111-4111-8111-111111111111",
        operation="conversation.respond",
        provider="openai",
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        attempt_number=1,
        created_at=datetime(
            2026,
            9,
            27,
            tzinfo=timezone.utc,
        ),
    )

    db.add(row)
    db.flush()

    return row


def test_calculates_execution_cost(db):
    rate = add_rate(db)

    execution = add_execution(db)

    result = calculate_ai_execution_cost(
        db,
        execution=execution,
    )

    assert result.execution_id == execution.id
    assert result.rate_id == rate.id

    # 500k tokens at $1 / million = $0.50
    assert result.input_cost_micro_usd == 500_000

    # 250k tokens at $2 / million = $0.50
    assert result.output_cost_micro_usd == 500_000

    assert result.total_cost_micro_usd == 1_000_000


def test_fractional_micro_usd_rounds_up():
    result = _token_cost_micro_usd(
        tokens=1,
        rate_per_million_micro_usd=1,
    )

    assert result == 1


def test_zero_tokens_cost_zero():
    result = _token_cost_micro_usd(
        tokens=0,
        rate_per_million_micro_usd=9_999_999,
    )

    assert result == 0


def test_missing_input_usage_fails_closed(db):
    add_rate(db)

    execution = add_execution(
        db,
        input_tokens=None,
    )

    with pytest.raises(
        AIExecutionUsageMissing
    ):
        calculate_ai_execution_cost(
            db,
            execution=execution,
        )


def test_missing_output_usage_fails_closed(db):
    add_rate(db)

    execution = add_execution(
        db,
        output_tokens=None,
    )

    with pytest.raises(
        AIExecutionUsageMissing
    ):
        calculate_ai_execution_cost(
            db,
            execution=execution,
        )


def test_missing_provider_rate_fails_closed(db):
    execution = add_execution(
        db,
        model="unpriced-model",
    )

    with pytest.raises(
        AICostRateNotFound
    ):
        calculate_ai_execution_cost(
            db,
            execution=execution,
        )


def test_historical_execution_uses_historical_rate(db):
    old_rate = AICostRate(
        provider="openai",
        model="example-model",
        input_cost_per_million_micro_usd=1_000_000,
        output_cost_per_million_micro_usd=2_000_000,
        effective_from=datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        ),
        effective_until=datetime(
            2026,
            10,
            1,
            tzinfo=timezone.utc,
        ),
    )

    new_rate = AICostRate(
        provider="openai",
        model="example-model",
        input_cost_per_million_micro_usd=5_000_000,
        output_cost_per_million_micro_usd=10_000_000,
        effective_from=datetime(
            2026,
            10,
            1,
            tzinfo=timezone.utc,
        ),
    )

    db.add_all(
        [
            old_rate,
            new_rate,
        ]
    )

    db.flush()

    execution = add_execution(
        db,
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )

    result = calculate_ai_execution_cost(
        db,
        execution=execution,
    )

    assert result.rate_id == old_rate.id
    assert result.input_cost_micro_usd == 1_000_000
    assert result.output_cost_micro_usd == 2_000_000
    assert result.total_cost_micro_usd == 3_000_000
