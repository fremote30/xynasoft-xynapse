"""
Database synchronization tests for the XynaFaith V2 commercial catalog.
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.core.product_catalog import (
    COMMERCIAL_PLANS,
    PLAN_CODE_CHURCH,
    PLAN_CODE_PASTOR_PRO,
)
from api.db.database import Base
from api.models.church import Church
from api.models.plan import Plan
from api.models.plan_entitlement import PlanEntitlement
from api.models.subscription import Subscription
from api.models.user import User
from api.services.product_catalog_sync import sync_product_catalog


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
            Church.__table__,
            User.__table__,
            Plan.__table__,
            PlanEntitlement.__table__,
            Subscription.__table__,
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


def _catalog_entitlement_count():
    return sum(
        len(plan.entitlements)
        for plan in COMMERCIAL_PLANS
    )


def test_initial_sync_creates_catalog_plans_and_entitlements(db):
    result = sync_product_catalog(db)

    assert result.plans_created == 3
    assert result.plans_updated == 0
    assert result.plans_unchanged == 0
    assert result.entitlements_created == _catalog_entitlement_count()
    assert result.entitlements_updated == 0
    assert result.entitlements_deleted == 0

    assert db.query(Plan).count() == 3
    assert (
        db.query(PlanEntitlement).count()
        == _catalog_entitlement_count()
    )


def test_second_sync_is_idempotent(db):
    sync_product_catalog(db)

    plan_ids_before = {
        plan.code: plan.id
        for plan in db.query(Plan).all()
    }

    result = sync_product_catalog(db)

    plan_ids_after = {
        plan.code: plan.id
        for plan in db.query(Plan).all()
    }

    assert result.plans_created == 0
    assert result.plans_updated == 0
    assert result.plans_unchanged == 3
    assert result.entitlements_created == 0
    assert result.entitlements_updated == 0
    assert result.entitlements_deleted == 0
    assert plan_ids_after == plan_ids_before


def test_sync_repairs_catalog_owned_plan_fields(db):
    sync_product_catalog(db)

    plan = (
        db.query(Plan)
        .filter(Plan.code == PLAN_CODE_PASTOR_PRO)
        .one()
    )

    original_id = plan.id

    plan.name = "Wrong Name"
    plan.access_profile = "wrong_profile"
    plan.owner_type = "wrong_owner"
    plan.is_active = False
    db.flush()

    result = sync_product_catalog(db)

    db.refresh(plan)

    assert result.plans_updated == 1
    assert plan.id == original_id
    assert plan.name == "Pastor Pro"
    assert plan.access_profile == "pastor_pro"
    assert plan.owner_type == "individual"
    assert plan.is_active is True


def test_sync_repairs_catalog_owned_entitlement_values(db):
    sync_product_catalog(db)

    plan = (
        db.query(Plan)
        .filter(Plan.code == PLAN_CODE_PASTOR_PRO)
        .one()
    )

    entitlement = (
        db.query(PlanEntitlement)
        .filter(
            PlanEntitlement.plan_id == plan.id,
            PlanEntitlement.entitlement_key == "xyniva.chat",
        )
        .one()
    )

    entitlement.enabled = False
    entitlement.usage_limit = 1
    entitlement.usage_period = "daily"
    db.flush()

    result = sync_product_catalog(db)

    db.refresh(entitlement)

    assert result.entitlements_updated == 1
    assert entitlement.enabled is True
    assert entitlement.usage_limit == 500
    assert entitlement.usage_period == "monthly"


def test_sync_recreates_missing_catalog_entitlement(db):
    sync_product_catalog(db)

    plan = (
        db.query(Plan)
        .filter(Plan.code == PLAN_CODE_PASTOR_PRO)
        .one()
    )

    entitlement = (
        db.query(PlanEntitlement)
        .filter(
            PlanEntitlement.plan_id == plan.id,
            PlanEntitlement.entitlement_key == "xyniva.chat",
        )
        .one()
    )

    db.delete(entitlement)
    db.flush()

    result = sync_product_catalog(db)

    assert result.entitlements_created == 1

    recreated = (
        db.query(PlanEntitlement)
        .filter(
            PlanEntitlement.plan_id == plan.id,
            PlanEntitlement.entitlement_key == "xyniva.chat",
        )
        .one()
    )

    assert recreated.usage_limit == 500
    assert recreated.usage_period == "monthly"


def test_sync_removes_stale_entitlement_from_catalog_owned_plan(db):
    sync_product_catalog(db)

    plan = (
        db.query(Plan)
        .filter(Plan.code == PLAN_CODE_CHURCH)
        .one()
    )

    db.add(
        PlanEntitlement(
            plan_id=plan.id,
            entitlement_key="legacy.experimental",
            enabled=True,
            usage_limit=7,
            usage_period="monthly",
        )
    )
    db.flush()

    result = sync_product_catalog(db)

    assert result.entitlements_deleted == 1

    assert (
        db.query(PlanEntitlement)
        .filter(
            PlanEntitlement.plan_id == plan.id,
            PlanEntitlement.entitlement_key == "legacy.experimental",
        )
        .count()
        == 0
    )


def test_sync_does_not_touch_unrelated_plan(db):
    unrelated = Plan(
        code="future_experiment",
        name="Future Experiment",
        access_profile="future_profile",
        owner_type="individual",
        is_active=True,
    )
    db.add(unrelated)
    db.flush()

    unrelated_id = unrelated.id

    sync_product_catalog(db)

    persisted = (
        db.query(Plan)
        .filter(Plan.code == "future_experiment")
        .one()
    )

    assert persisted.id == unrelated_id
    assert persisted.name == "Future Experiment"
    assert persisted.access_profile == "future_profile"
    assert persisted.owner_type == "individual"
    assert persisted.is_active is True


def test_sync_does_not_commit_caller_transaction(db):
    sync_product_catalog(db)

    assert db.in_transaction()

    db.rollback()

    assert db.query(Plan).count() == 0


def test_sync_preserves_existing_plan_id_and_subscription(db):
    sync_product_catalog(db)

    plan = (
        db.query(Plan)
        .filter(Plan.code == PLAN_CODE_PASTOR_PRO)
        .one()
    )

    plan_id = plan.id

    user = User(
        name="Catalog Subscription User",
        email="catalog-subscription@example.com",
        role="pastor",
        is_verified=True,
    )
    db.add(user)
    db.flush()

    subscription = Subscription(
        plan_id=plan.id,
        user_id=user.id,
        church_id=None,
        status="active",
    )
    db.add(subscription)
    db.flush()

    subscription_id = subscription.id

    plan.name = "Needs Repair"
    db.flush()

    sync_product_catalog(db)

    assert plan.id == plan_id
    assert subscription.id == subscription_id
    assert subscription.plan_id == plan_id
    assert subscription.status == "active"
