from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from xynassist_service.core.ai_cost_catalog import (
    CatalogAICostRate,
    validate_ai_cost_catalog,
)
from xynassist_service.db.database import Base
import xynassist_service.models  # noqa: F401
from xynassist_service.models.ai_cost_rate import (
    AICostRate,
)
from xynassist_service.services.ai_cost_catalog_sync import (
    AICostCatalogConfigurationError,
    sync_ai_cost_catalog,
)
from xynassist_service.services.ai_cost_rates import (
    AICostRateConfigurationError,
    AICostRateNotFound,
    resolve_ai_cost_rate,
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


def rate(
    *,
    input_cost=1_000_000,
    output_cost=2_000_000,
):
    return CatalogAICostRate(
        provider="OpenAI",
        model="example-model",
        input_cost_per_million_micro_usd=input_cost,
        output_cost_per_million_micro_usd=output_cost,
    )


def test_catalog_normalizes_and_validates():
    result = validate_ai_cost_catalog(
        [rate()]
    )

    assert result[0].provider == "openai"
    assert result[0].model == "example-model"


def test_catalog_rejects_duplicate_provider_model():
    with pytest.raises(ValueError):
        validate_ai_cost_catalog(
            [
                rate(),
                rate(),
            ]
        )


def test_sync_creates_and_resolves_rate(db):
    now = datetime(
        2026,
        9,
        27,
        tzinfo=timezone.utc,
    )

    result = sync_ai_cost_catalog(
        db,
        rates=[rate()],
        now=now,
    )

    assert result.rates_created == 1
    assert result.rates_transitioned == 0

    resolved = resolve_ai_cost_rate(
        db,
        provider="OPENAI",
        model="example-model",
        occurred_at=now,
    )

    assert (
        resolved.input_cost_per_million_micro_usd
        == 1_000_000
    )

    assert (
        resolved.output_cost_per_million_micro_usd
        == 2_000_000
    )


def test_sync_preserves_history_on_change(db):
    first = datetime(
        2026,
        9,
        1,
        tzinfo=timezone.utc,
    )

    second = datetime(
        2026,
        10,
        1,
        tzinfo=timezone.utc,
    )

    sync_ai_cost_catalog(
        db,
        rates=[rate()],
        now=first,
    )

    sync_ai_cost_catalog(
        db,
        rates=[
            rate(
                input_cost=2_000_000,
                output_cost=4_000_000,
            )
        ],
        now=second,
    )

    rows = (
        db.query(AICostRate)
        .order_by(
            AICostRate.effective_from.asc()
        )
        .all()
    )

    assert len(rows) == 2

    # SQLite does not preserve timezone information for DateTime
    # values even when timezone=True. Compare the wall-clock value
    # here; production PostgreSQL retains the timezone-aware contract.
    assert (
        rows[0].effective_until
        == second.replace(tzinfo=None)
    )

    assert rows[1].effective_until is None

    old = resolve_ai_cost_rate(
        db,
        provider="openai",
        model="example-model",
        occurred_at=(
            first
            + timedelta(days=10)
        ),
    )

    current = resolve_ai_cost_rate(
        db,
        provider="openai",
        model="example-model",
        occurred_at=second,
    )

    assert (
        old.input_cost_per_million_micro_usd
        == 1_000_000
    )

    assert (
        current.input_cost_per_million_micro_usd
        == 2_000_000
    )


def test_unchanged_sync_does_not_duplicate(db):
    now = datetime(
        2026,
        9,
        27,
        tzinfo=timezone.utc,
    )

    sync_ai_cost_catalog(
        db,
        rates=[rate()],
        now=now,
    )

    result = sync_ai_cost_catalog(
        db,
        rates=[rate()],
        now=now + timedelta(days=1),
    )

    assert result.rates_created == 0
    assert result.rates_transitioned == 0
    assert result.rates_unchanged == 1

    assert db.query(AICostRate).count() == 1


def test_resolver_fails_when_rate_missing(db):
    with pytest.raises(AICostRateNotFound):
        resolve_ai_cost_rate(
            db,
            provider="openai",
            model="missing",
            occurred_at=datetime.now(
                timezone.utc
            ),
        )


def test_resolver_fails_closed_on_ambiguity(db):
    now = datetime.now(timezone.utc)

    db.add_all(
        [
            AICostRate(
                provider="openai",
                model="example-model",
                input_cost_per_million_micro_usd=1,
                output_cost_per_million_micro_usd=2,
                effective_from=(
                    now - timedelta(days=2)
                ),
            ),
            AICostRate(
                provider="openai",
                model="example-model",
                input_cost_per_million_micro_usd=3,
                output_cost_per_million_micro_usd=4,
                effective_from=(
                    now - timedelta(days=1)
                ),
            ),
        ]
    )

    db.flush()

    with pytest.raises(
        AICostRateConfigurationError
    ):
        resolve_ai_cost_rate(
            db,
            provider="openai",
            model="example-model",
            occurred_at=now,
        )


def test_sync_fails_closed_on_future_rate(db):
    now = datetime.now(timezone.utc)

    db.add(
        AICostRate(
            provider="openai",
            model="example-model",
            input_cost_per_million_micro_usd=1,
            output_cost_per_million_micro_usd=2,
            effective_from=(
                now + timedelta(days=1)
            ),
        )
    )

    db.flush()

    with pytest.raises(
        AICostCatalogConfigurationError
    ):
        sync_ai_cost_catalog(
            db,
            rates=[rate()],
            now=now,
        )
