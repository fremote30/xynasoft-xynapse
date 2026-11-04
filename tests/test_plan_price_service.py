"""
Contract tests for XynaFaith V2 commercial price resolution.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db.database import Base
from api.models.plan import Plan
from api.models.plan_entitlement import PlanEntitlement
from api.models.plan_price import PlanPrice
from api.models.subscription import Subscription
from api.services.plan_price_service import (
    GLOBAL_MARKET_CODE,
    PriceConfigurationError,
    PriceNotFound,
    resolve_plan_price,
)


NOW = datetime(2026, 9, 26, 12, 0, 0)


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(
        engine,
        tables=[
            Plan.__table__,
            PlanEntitlement.__table__,
            Subscription.__table__,
            PlanPrice.__table__,
        ],
    )

    TestingSession = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    session = TestingSession()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def plan(db):
    value = Plan(
        code="pastor_pro",
        name="Pastor Pro",
        access_profile="pastor_pro",
        owner_type="individual",
        is_active=True,
    )
    db.add(value)
    db.flush()
    return value


def add_price(
    db,
    plan,
    *,
    market_code,
    currency,
    billing_interval="monthly",
    amount_minor=1000,
    is_active=True,
    effective_from=None,
    effective_until=None,
):
    value = PlanPrice(
        plan_id=plan.id,
        market_code=market_code,
        currency=currency,
        billing_interval=billing_interval,
        amount_minor=amount_minor,
        is_active=is_active,
        effective_from=effective_from or (NOW - timedelta(days=1)),
        effective_until=effective_until,
    )
    db.add(value)
    db.flush()
    return value


def test_exact_market_price_resolves(db, plan):
    price = add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
        amount_minor=15000,
    )

    result = resolve_plan_price(
        db,
        plan_code="pastor_pro",
        market_code="GH",
        billing_interval="monthly",
        now=NOW,
    )

    assert result.price_id == price.id
    assert result.market_code == "GH"
    assert result.requested_market_code == "GH"
    assert result.currency == "GHS"
    assert result.amount_minor == 15000
    assert result.used_global_fallback is False


def test_market_code_is_normalized(db, plan):
    add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
        amount_minor=15000,
    )

    result = resolve_plan_price(
        db,
        plan_code="pastor_pro",
        market_code=" gh ",
        billing_interval="MONTHLY",
        now=NOW,
    )

    assert result.market_code == "GH"
    assert result.billing_interval == "monthly"


def test_exact_market_wins_over_global(db, plan):
    exact = add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
        amount_minor=15000,
    )
    add_price(
        db,
        plan,
        market_code=GLOBAL_MARKET_CODE,
        currency="USD",
        amount_minor=1000,
    )

    result = resolve_plan_price(
        db,
        plan_code="pastor_pro",
        market_code="GH",
        billing_interval="monthly",
        now=NOW,
    )

    assert result.price_id == exact.id
    assert result.currency == "GHS"
    assert result.used_global_fallback is False


def test_global_fallback_used_when_exact_market_missing(db, plan):
    fallback = add_price(
        db,
        plan,
        market_code=GLOBAL_MARKET_CODE,
        currency="USD",
        amount_minor=1000,
    )

    result = resolve_plan_price(
        db,
        plan_code="pastor_pro",
        market_code="NG",
        billing_interval="monthly",
        now=NOW,
    )

    assert result.price_id == fallback.id
    assert result.market_code == GLOBAL_MARKET_CODE
    assert result.requested_market_code == "NG"
    assert result.currency == "USD"
    assert result.used_global_fallback is True


def test_global_request_does_not_double_resolve(db, plan):
    global_price = add_price(
        db,
        plan,
        market_code=GLOBAL_MARKET_CODE,
        currency="USD",
    )

    result = resolve_plan_price(
        db,
        plan_code="pastor_pro",
        market_code=GLOBAL_MARKET_CODE,
        billing_interval="monthly",
        now=NOW,
    )

    assert result.price_id == global_price.id
    assert result.used_global_fallback is False


def test_monthly_does_not_fall_back_to_annual(db, plan):
    add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
        billing_interval="annual",
        amount_minor=150000,
    )

    with pytest.raises(PriceNotFound):
        resolve_plan_price(
            db,
            plan_code="pastor_pro",
            market_code="GH",
            billing_interval="monthly",
            now=NOW,
        )


def test_inactive_price_is_ignored(db, plan):
    add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
        is_active=False,
    )

    with pytest.raises(PriceNotFound):
        resolve_plan_price(
            db,
            plan_code="pastor_pro",
            market_code="GH",
            billing_interval="monthly",
            now=NOW,
        )


def test_future_price_is_ignored(db, plan):
    add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
        effective_from=NOW + timedelta(days=1),
    )

    with pytest.raises(PriceNotFound):
        resolve_plan_price(
            db,
            plan_code="pastor_pro",
            market_code="GH",
            billing_interval="monthly",
            now=NOW,
        )


def test_expired_price_is_ignored(db, plan):
    add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
        effective_from=NOW - timedelta(days=10),
        effective_until=NOW,
    )

    with pytest.raises(PriceNotFound):
        resolve_plan_price(
            db,
            plan_code="pastor_pro",
            market_code="GH",
            billing_interval="monthly",
            now=NOW,
        )


def test_effective_until_is_exclusive(db, plan):
    add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
        effective_from=NOW - timedelta(days=1),
        effective_until=NOW,
    )

    replacement = add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
        amount_minor=20000,
        effective_from=NOW,
        effective_until=None,
    )

    result = resolve_plan_price(
        db,
        plan_code="pastor_pro",
        market_code="GH",
        billing_interval="monthly",
        now=NOW,
    )

    assert result.price_id == replacement.id
    assert result.amount_minor == 20000


def test_inactive_plan_is_not_sellable(db, plan):
    add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
    )

    plan.is_active = False
    db.flush()

    with pytest.raises(PriceNotFound):
        resolve_plan_price(
            db,
            plan_code="pastor_pro",
            market_code="GH",
            billing_interval="monthly",
            now=NOW,
        )


def test_unknown_plan_is_not_found(db):
    with pytest.raises(PriceNotFound):
        resolve_plan_price(
            db,
            plan_code="does_not_exist",
            market_code="GH",
            billing_interval="monthly",
            now=NOW,
        )


def test_multiple_current_exact_prices_fail_closed(db, plan):
    add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
        amount_minor=15000,
    )
    add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
        amount_minor=16000,
        effective_from=NOW - timedelta(hours=1),
    )

    with pytest.raises(PriceConfigurationError):
        resolve_plan_price(
            db,
            plan_code="pastor_pro",
            market_code="GH",
            billing_interval="monthly",
            now=NOW,
        )


def test_multiple_current_global_prices_fail_closed(db, plan):
    add_price(
        db,
        plan,
        market_code=GLOBAL_MARKET_CODE,
        currency="USD",
        amount_minor=1000,
    )
    add_price(
        db,
        plan,
        market_code=GLOBAL_MARKET_CODE,
        currency="USD",
        amount_minor=1200,
        effective_from=NOW - timedelta(hours=1),
    )

    with pytest.raises(PriceConfigurationError):
        resolve_plan_price(
            db,
            plan_code="pastor_pro",
            market_code="NG",
            billing_interval="monthly",
            now=NOW,
        )


def test_exact_market_ambiguity_does_not_fall_back_to_global(db, plan):
    add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
        amount_minor=15000,
    )
    add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
        amount_minor=16000,
        effective_from=NOW - timedelta(hours=1),
    )
    add_price(
        db,
        plan,
        market_code=GLOBAL_MARKET_CODE,
        currency="USD",
        amount_minor=1000,
    )

    with pytest.raises(PriceConfigurationError):
        resolve_plan_price(
            db,
            plan_code="pastor_pro",
            market_code="GH",
            billing_interval="monthly",
            now=NOW,
        )


@pytest.mark.parametrize(
    "billing_interval",
    [
        "",
        "weekly",
        "quarterly",
    ],
)
def test_invalid_billing_interval_rejected(db, plan, billing_interval):
    with pytest.raises(ValueError):
        resolve_plan_price(
            db,
            plan_code="pastor_pro",
            market_code="GH",
            billing_interval=billing_interval,
            now=NOW,
        )


@pytest.mark.parametrize(
    "market_code",
    [
        "",
        "   ",
    ],
)
def test_blank_market_rejected(db, plan, market_code):
    with pytest.raises(ValueError):
        resolve_plan_price(
            db,
            plan_code="pastor_pro",
            market_code=market_code,
            billing_interval="monthly",
            now=NOW,
        )


def test_blank_plan_code_rejected(db):
    with pytest.raises(ValueError):
        resolve_plan_price(
            db,
            plan_code=" ",
            market_code="GH",
            billing_interval="monthly",
            now=NOW,
        )


def test_resolution_is_read_only(db, plan):
    add_price(
        db,
        plan,
        market_code="GH",
        currency="GHS",
        amount_minor=15000,
    )
    db.commit()

    result = resolve_plan_price(
        db,
        plan_code="pastor_pro",
        market_code="GH",
        billing_interval="monthly",
        now=NOW,
    )

    assert result.amount_minor == 15000
    assert not db.new
    assert not db.dirty
    assert not db.deleted
