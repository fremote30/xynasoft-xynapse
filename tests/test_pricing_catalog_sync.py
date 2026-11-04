from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.core.pricing_catalog import CatalogPrice
from api.db.database import Base
from api.models.plan import Plan
from api.models.plan_price import PlanPrice
from api.services.pricing_catalog_sync import (
    PricingCatalogConfigurationError,
    PricingCatalogPlanError,
    sync_pricing_catalog,
)


NOW = datetime(2026, 9, 27, 12, 0, 0)


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
def pastor_pro(db):
    plan = Plan(
        code="pastor_pro",
        name="Pastor Pro",
        access_profile="pastor_pro",
        owner_type="individual",
        is_active=True,
    )
    db.add(plan)
    db.flush()
    return plan


def catalog_price(
    *,
    plan_code="pastor_pro",
    market_code="GH",
    currency="GHS",
    billing_interval="monthly",
    amount_minor=10000,
):
    return CatalogPrice(
        plan_code=plan_code,
        market_code=market_code,
        currency=currency,
        billing_interval=billing_interval,
        amount_minor=amount_minor,
    )


def add_price(
    db,
    *,
    plan_id,
    market_code="GH",
    currency="GHS",
    billing_interval="monthly",
    amount_minor=10000,
    effective_from=None,
    effective_until=None,
    is_active=True,
):
    value = PlanPrice(
        plan_id=plan_id,
        market_code=market_code,
        currency=currency,
        billing_interval=billing_interval,
        amount_minor=amount_minor,
        is_active=is_active,
        effective_from=effective_from or (NOW - timedelta(days=30)),
        effective_until=effective_until,
    )
    db.add(value)
    db.flush()
    return value


def test_initial_sync_creates_current_price(db, pastor_pro):
    result = sync_pricing_catalog(
        db,
        [catalog_price()],
        now=NOW,
    )

    assert result.prices_created == 1
    assert result.prices_transitioned == 0
    assert result.prices_unchanged == 0

    stored = db.query(PlanPrice).one()
    assert stored.plan_id == pastor_pro.id
    assert stored.market_code == "GH"
    assert stored.currency == "GHS"
    assert stored.billing_interval == "monthly"
    assert stored.amount_minor == 10000
    assert stored.is_active is True
    assert stored.effective_from == NOW
    assert stored.effective_until is None


def test_second_sync_is_idempotent(db, pastor_pro):
    sync_pricing_catalog(db, [catalog_price()], now=NOW)

    stored = db.query(PlanPrice).one()
    original_id = stored.id
    original_effective_from = stored.effective_from

    result = sync_pricing_catalog(
        db,
        [catalog_price()],
        now=NOW + timedelta(days=1),
    )

    assert result.prices_created == 0
    assert result.prices_transitioned == 0
    assert result.prices_unchanged == 1

    prices = db.query(PlanPrice).all()
    assert len(prices) == 1
    assert prices[0].id == original_id
    assert prices[0].effective_from == original_effective_from
    assert prices[0].effective_until is None


def test_changed_amount_closes_old_price_and_creates_successor(
    db,
    pastor_pro,
):
    old = add_price(
        db,
        plan_id=pastor_pro.id,
        amount_minor=10000,
    )

    result = sync_pricing_catalog(
        db,
        [catalog_price(amount_minor=12000)],
        now=NOW,
    )

    assert result.prices_created == 1
    assert result.prices_transitioned == 1
    assert result.prices_unchanged == 0

    db.refresh(old)
    assert old.amount_minor == 10000
    assert old.effective_until == NOW

    prices = (
        db.query(PlanPrice)
        .order_by(PlanPrice.effective_from)
        .all()
    )
    assert len(prices) == 2
    assert prices[1].amount_minor == 12000
    assert prices[1].effective_from == NOW
    assert prices[1].effective_until is None


def test_currency_change_is_historical_transition(db, pastor_pro):
    old = add_price(
        db,
        plan_id=pastor_pro.id,
        currency="GHS",
        amount_minor=10000,
    )

    result = sync_pricing_catalog(
        db,
        [
            catalog_price(
                currency="USD",
                amount_minor=2000,
            )
        ],
        now=NOW,
    )

    assert result.prices_created == 1
    assert result.prices_transitioned == 1

    db.refresh(old)
    assert old.currency == "GHS"
    assert old.amount_minor == 10000
    assert old.effective_until == NOW

    current = (
        db.query(PlanPrice)
        .filter(PlanPrice.effective_until.is_(None))
        .one()
    )
    assert current.currency == "USD"
    assert current.amount_minor == 2000


def test_existing_historical_rows_are_preserved(db, pastor_pro):
    historical = add_price(
        db,
        plan_id=pastor_pro.id,
        amount_minor=8000,
        effective_from=NOW - timedelta(days=90),
        effective_until=NOW - timedelta(days=30),
    )
    current = add_price(
        db,
        plan_id=pastor_pro.id,
        amount_minor=10000,
        effective_from=NOW - timedelta(days=30),
    )

    historical_id = historical.id
    current_id = current.id

    sync_pricing_catalog(
        db,
        [catalog_price(amount_minor=12000)],
        now=NOW,
    )

    rows = (
        db.query(PlanPrice)
        .order_by(PlanPrice.effective_from)
        .all()
    )

    assert len(rows) == 3
    assert rows[0].id == historical_id
    assert rows[0].amount_minor == 8000
    assert rows[0].effective_until == NOW - timedelta(days=30)

    assert rows[1].id == current_id
    assert rows[1].amount_minor == 10000
    assert rows[1].effective_until == NOW

    assert rows[2].amount_minor == 12000
    assert rows[2].effective_from == NOW


def test_catalog_omission_does_not_remove_existing_price(db, pastor_pro):
    existing = add_price(
        db,
        plan_id=pastor_pro.id,
        amount_minor=10000,
    )
    existing_id = existing.id

    result = sync_pricing_catalog(
        db,
        [],
        now=NOW,
    )

    assert result.prices_created == 0
    assert result.prices_transitioned == 0
    assert result.prices_unchanged == 0

    stored = db.query(PlanPrice).one()
    assert stored.id == existing_id
    assert stored.effective_until is None
    assert stored.is_active is True


def test_different_market_is_not_touched(db, pastor_pro):
    us = add_price(
        db,
        plan_id=pastor_pro.id,
        market_code="US",
        currency="USD",
        amount_minor=1900,
    )
    us_id = us.id

    sync_pricing_catalog(
        db,
        [catalog_price()],
        now=NOW,
    )

    stored_us = (
        db.query(PlanPrice)
        .filter(PlanPrice.market_code == "US")
        .one()
    )
    assert stored_us.id == us_id
    assert stored_us.amount_minor == 1900
    assert stored_us.effective_until is None


def test_different_billing_interval_is_not_touched(db, pastor_pro):
    annual = add_price(
        db,
        plan_id=pastor_pro.id,
        billing_interval="annual",
        amount_minor=100000,
    )
    annual_id = annual.id

    sync_pricing_catalog(
        db,
        [catalog_price()],
        now=NOW,
    )

    stored_annual = (
        db.query(PlanPrice)
        .filter(PlanPrice.billing_interval == "annual")
        .one()
    )
    assert stored_annual.id == annual_id
    assert stored_annual.amount_minor == 100000
    assert stored_annual.effective_until is None


def test_multiple_current_prices_fail_closed(db, pastor_pro):
    add_price(
        db,
        plan_id=pastor_pro.id,
        amount_minor=10000,
    )
    add_price(
        db,
        plan_id=pastor_pro.id,
        amount_minor=11000,
        effective_from=NOW - timedelta(days=10),
    )

    with pytest.raises(PricingCatalogConfigurationError):
        sync_pricing_catalog(
            db,
            [catalog_price(amount_minor=12000)],
            now=NOW,
        )

    assert db.query(PlanPrice).count() == 2


def test_missing_plan_fails_closed(db):
    with pytest.raises(PricingCatalogPlanError):
        sync_pricing_catalog(
            db,
            [catalog_price()],
            now=NOW,
        )

    assert db.query(PlanPrice).count() == 0


def test_inactive_plan_fails_closed(db, pastor_pro):
    pastor_pro.is_active = False
    db.flush()

    with pytest.raises(PricingCatalogPlanError):
        sync_pricing_catalog(
            db,
            [catalog_price()],
            now=NOW,
        )

    assert db.query(PlanPrice).count() == 0


def test_sync_does_not_commit_caller_transaction(db, pastor_pro):
    sync_pricing_catalog(
        db,
        [catalog_price()],
        now=NOW,
    )

    assert db.in_transaction()
    assert db.query(PlanPrice).count() == 1

    db.rollback()

    assert db.query(PlanPrice).count() == 0


def test_normalized_catalog_values_are_persisted(db, pastor_pro):
    sync_pricing_catalog(
        db,
        [
            catalog_price(
                plan_code=" pastor_pro ",
                market_code=" gh ",
                currency=" ghs ",
                billing_interval=" MONTHLY ",
            )
        ],
        now=NOW,
    )

    stored = db.query(PlanPrice).one()
    assert stored.market_code == "GH"
    assert stored.currency == "GHS"
    assert stored.billing_interval == "monthly"


def test_future_scheduled_price_fails_closed_without_current_price(
    db,
    pastor_pro,
):
    future = add_price(
        db,
        plan_id=pastor_pro.id,
        amount_minor=12000,
        effective_from=NOW + timedelta(days=30),
    )
    future_id = future.id

    with pytest.raises(
        PricingCatalogConfigurationError,
        match="Active future-scheduled price exists",
    ):
        sync_pricing_catalog(
            db,
            [catalog_price(amount_minor=10000)],
            now=NOW,
        )

    rows = db.query(PlanPrice).all()

    assert len(rows) == 1
    assert rows[0].id == future_id
    assert rows[0].effective_from == NOW + timedelta(days=30)
    assert rows[0].effective_until is None


def test_future_scheduled_price_fails_closed_with_current_price(
    db,
    pastor_pro,
):
    current = add_price(
        db,
        plan_id=pastor_pro.id,
        amount_minor=10000,
        effective_from=NOW - timedelta(days=30),
    )
    future = add_price(
        db,
        plan_id=pastor_pro.id,
        amount_minor=12000,
        effective_from=NOW + timedelta(days=30),
    )

    current_id = current.id
    future_id = future.id

    with pytest.raises(
        PricingCatalogConfigurationError,
        match="Active future-scheduled price exists",
    ):
        sync_pricing_catalog(
            db,
            [catalog_price(amount_minor=11000)],
            now=NOW,
        )

    rows = (
        db.query(PlanPrice)
        .order_by(PlanPrice.effective_from)
        .all()
    )

    assert len(rows) == 2
    assert rows[0].id == current_id
    assert rows[0].amount_minor == 10000
    assert rows[0].effective_until is None
    assert rows[1].id == future_id
    assert rows[1].amount_minor == 12000
    assert rows[1].effective_until is None


def test_inactive_future_price_does_not_block_sync(
    db,
    pastor_pro,
):
    add_price(
        db,
        plan_id=pastor_pro.id,
        amount_minor=12000,
        effective_from=NOW + timedelta(days=30),
        is_active=False,
    )

    result = sync_pricing_catalog(
        db,
        [catalog_price(amount_minor=10000)],
        now=NOW,
    )

    assert result.prices_created == 1
    assert result.prices_transitioned == 0
    assert result.prices_unchanged == 0

    active = (
        db.query(PlanPrice)
        .filter(PlanPrice.is_active.is_(True))
        .one()
    )

    assert active.amount_minor == 10000
    assert active.effective_from == NOW
    assert active.effective_until is None


def test_future_price_for_different_market_does_not_block_sync(
    db,
    pastor_pro,
):
    add_price(
        db,
        plan_id=pastor_pro.id,
        market_code="US",
        currency="USD",
        amount_minor=1900,
        effective_from=NOW + timedelta(days=30),
    )

    result = sync_pricing_catalog(
        db,
        [catalog_price()],
        now=NOW,
    )

    assert result.prices_created == 1
    assert result.prices_transitioned == 0
    assert result.prices_unchanged == 0
