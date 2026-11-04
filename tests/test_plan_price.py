"""
Contract tests for XynaFaith V2 provider-agnostic plan pricing.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db.database import Base
from api.models.plan import Plan
from api.models.plan_entitlement import PlanEntitlement
from api.models.plan_price import (
    BILLING_INTERVAL_ANNUAL,
    BILLING_INTERVAL_MONTHLY,
    BILLING_INTERVALS,
    PlanPrice,
)
from api.models.subscription import Subscription


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
        code="pricing_test",
        name="Pricing Test",
        access_profile="pastor_pro",
        owner_type="individual",
        is_active=True,
    )
    db.add(value)
    db.flush()
    return value


def test_billing_interval_vocabulary_is_explicit():
    assert BILLING_INTERVAL_MONTHLY == "monthly"
    assert BILLING_INTERVAL_ANNUAL == "annual"
    assert BILLING_INTERVALS == {"monthly", "annual"}


def test_plan_price_stores_provider_agnostic_commercial_price(db, plan):
    price = PlanPrice(
        plan_id=plan.id,
        market_code="GH",
        currency="GHS",
        billing_interval=BILLING_INTERVAL_MONTHLY,
        amount_minor=10000,
        effective_from=datetime.utcnow(),
    )

    db.add(price)
    db.commit()
    db.refresh(price)

    assert price.plan_id == plan.id
    assert price.market_code == "GH"
    assert price.currency == "GHS"
    assert price.billing_interval == "monthly"
    assert price.amount_minor == 10000
    assert price.is_active is True
    assert price.effective_until is None


def test_plan_price_relationship_resolves_plan(db, plan):
    price = PlanPrice(
        plan_id=plan.id,
        market_code="US",
        currency="USD",
        billing_interval=BILLING_INTERVAL_ANNUAL,
        amount_minor=12000,
        effective_from=datetime.utcnow(),
    )

    db.add(price)
    db.commit()

    assert price.plan.id == plan.id
    assert price.plan.code == "pricing_test"
    assert price in plan.prices


def test_plan_can_have_multiple_market_prices(db, plan):
    db.add_all(
        [
            PlanPrice(
                plan_id=plan.id,
                market_code="US",
                currency="USD",
                billing_interval="monthly",
                amount_minor=1000,
                effective_from=datetime.utcnow(),
            ),
            PlanPrice(
                plan_id=plan.id,
                market_code="GH",
                currency="GHS",
                billing_interval="monthly",
                amount_minor=15000,
                effective_from=datetime.utcnow(),
            ),
        ]
    )

    db.commit()

    assert (
        db.query(PlanPrice)
        .filter(PlanPrice.plan_id == plan.id)
        .count()
        == 2
    )


def test_plan_can_have_monthly_and_annual_prices(db, plan):
    db.add_all(
        [
            PlanPrice(
                plan_id=plan.id,
                market_code="US",
                currency="USD",
                billing_interval="monthly",
                amount_minor=1000,
                effective_from=datetime.utcnow(),
            ),
            PlanPrice(
                plan_id=plan.id,
                market_code="US",
                currency="USD",
                billing_interval="annual",
                amount_minor=10000,
                effective_from=datetime.utcnow(),
            ),
        ]
    )

    db.commit()

    intervals = {
        price.billing_interval
        for price in db.query(PlanPrice)
        .filter(PlanPrice.plan_id == plan.id)
        .all()
    }

    assert intervals == {"monthly", "annual"}


def test_price_history_can_have_successive_effective_periods(db, plan):
    first_start = datetime(2026, 1, 1)
    second_start = datetime(2026, 7, 1)

    db.add_all(
        [
            PlanPrice(
                plan_id=plan.id,
                market_code="GH",
                currency="GHS",
                billing_interval="monthly",
                amount_minor=10000,
                effective_from=first_start,
                effective_until=second_start,
                is_active=False,
            ),
            PlanPrice(
                plan_id=plan.id,
                market_code="GH",
                currency="GHS",
                billing_interval="monthly",
                amount_minor=12000,
                effective_from=second_start,
                effective_until=None,
                is_active=True,
            ),
        ]
    )

    db.commit()

    prices = (
        db.query(PlanPrice)
        .filter(PlanPrice.plan_id == plan.id)
        .order_by(PlanPrice.effective_from)
        .all()
    )

    assert len(prices) == 2
    assert prices[0].amount_minor == 10000
    assert prices[0].effective_until == second_start
    assert prices[1].amount_minor == 12000
    assert prices[1].effective_until is None


def test_negative_amount_is_rejected(db, plan):
    db.add(
        PlanPrice(
            plan_id=plan.id,
            market_code="GH",
            currency="GHS",
            billing_interval="monthly",
            amount_minor=-1,
            effective_from=datetime.utcnow(),
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_unknown_billing_interval_is_rejected(db, plan):
    db.add(
        PlanPrice(
            plan_id=plan.id,
            market_code="GH",
            currency="GHS",
            billing_interval="weekly",
            amount_minor=1000,
            effective_from=datetime.utcnow(),
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_invalid_effective_period_is_rejected(db, plan):
    start = datetime.utcnow()

    db.add(
        PlanPrice(
            plan_id=plan.id,
            market_code="GH",
            currency="GHS",
            billing_interval="monthly",
            amount_minor=1000,
            effective_from=start,
            effective_until=start - timedelta(days=1),
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_equal_effective_boundaries_are_rejected(db, plan):
    boundary = datetime.utcnow()

    db.add(
        PlanPrice(
            plan_id=plan.id,
            market_code="GH",
            currency="GHS",
            billing_interval="monthly",
            amount_minor=1000,
            effective_from=boundary,
            effective_until=boundary,
        )
    )

    with pytest.raises(IntegrityError):
        db.commit()

    db.rollback()


def test_deleting_plan_cascades_prices(db, plan):
    price = PlanPrice(
        plan_id=plan.id,
        market_code="GH",
        currency="GHS",
        billing_interval="monthly",
        amount_minor=1000,
        effective_from=datetime.utcnow(),
    )

    db.add(price)
    db.commit()

    assert db.query(PlanPrice).count() == 1

    db.delete(plan)
    db.commit()

    assert db.query(PlanPrice).count() == 0


def test_plan_price_contains_no_payment_provider_identity():
    columns = set(PlanPrice.__table__.columns.keys())

    forbidden = {
        "stripe_product_id",
        "stripe_price_id",
        "provider",
        "provider_product_id",
        "provider_price_id",
        "payment_provider",
    }

    assert columns.isdisjoint(forbidden)
