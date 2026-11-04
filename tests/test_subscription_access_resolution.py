"""
XynaFaith V2 Subscription Access Resolution Tests.

Validates:

- Free member baseline access
- Active subscription upgrades
- Plan entitlement resolution
- Expired subscription fallback
- Feature gate behavior
"""

from datetime import datetime, timedelta

import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db.database import Base

from api.models.user import User
from api.models.plan import Plan
from api.models.plan_entitlement import PlanEntitlement
from api.models.subscription import Subscription


from api.services.effective_access_service import (
    get_effective_access,
    has_entitlement,
    check_feature_gate,
)


@pytest.fixture()
def db():

    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Plan.__table__,
            PlanEntitlement.__table__,
            Subscription.__table__,
        ],
    )

    Session = sessionmaker(
        bind=engine
    )

    session = Session()

    try:
        yield session

    finally:
        session.close()
        engine.dispose()



@pytest.fixture()
def member(db):

    user = User(
        name="Subscription Test User",
        email="subscription@test.com",
        password="password",
        role="member",
        is_verified=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user



def create_plan(
    db,
    *,
    code,
    profile,
    entitlements,
):

    plan = Plan(
        code=code,
        name=code.replace("_", " ").title(),
        access_profile=profile,
        owner_type="individual",
        is_active=True,
    )

    db.add(plan)
    db.commit()
    db.refresh(plan)


    for item in entitlements:

        entitlement = PlanEntitlement(
            plan_id=plan.id,
            entitlement_key=item["key"],
            enabled=True,
            usage_limit=item.get(
                "limit"
            ),
            usage_period="monthly",
        )

        db.add(entitlement)


    db.commit()

    return plan



def attach_subscription(
    db,
    *,
    user,
    plan,
    end=None,
):

    subscription = Subscription(
        plan_id=plan.id,
        user_id=user.id,
        status="active",
        current_period_start=datetime.utcnow(),
        current_period_end=end,
    )

    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    return subscription



def test_free_member_without_subscription(
    db,
    member,
):

    access = get_effective_access(
        db,
        member,
    )


    assert (
        access.access_profile
        ==
        "free_member"
    )


    assert has_entitlement(
        db,
        member,
        "xyniva.chat",
    )


    assert not has_entitlement(
        db,
        member,
        "sermon.studio",
    )



def test_active_subscription_adds_plan_entitlements(
    db,
    member,
):

    plan = create_plan(
        db,
        code="pastor_pro",
        profile="pastor_pro",
        entitlements=[
            {
                "key": "sermon.studio",
                "limit": 100,
            },
            {
                "key": "xyniva.chat",
                "limit": 500,
            },
        ],
    )


    attach_subscription(
        db,
        user=member,
        plan=plan,
    )


    access = get_effective_access(
        db,
        member,
    )


    assert (
        access.plan_code
        ==
        "pastor_pro"
    )

    assert (
        access.access_profile
        ==
        "pastor_pro"
    )

    # The paid plan expands the effective profile, but source_profile
    # preserves the role-aware free baseline from which access originated.
    assert (
        access.source_profile
        ==
        "free_member"
    )


    assert has_entitlement(
        db,
        member,
        "sermon.studio",
    )


    assert access.limits[
        "xyniva.chat"
    ] == 500



def test_expired_subscription_falls_back_to_baseline(
    db,
    member,
):

    plan = create_plan(
        db,
        code="expired_pro",
        profile="pastor_pro",
        entitlements=[
            {
                "key": "sermon.studio",
            }
        ],
    )


    attach_subscription(
        db,
        user=member,
        plan=plan,
        end=datetime.utcnow()
        -
        timedelta(days=1),
    )


    access = get_effective_access(
        db,
        member,
    )


    assert (
        access.plan_code
        is None
    )


    assert not has_entitlement(
        db,
        member,
        "sermon.studio",
    )



def test_feature_gate_paid_feature(
    db,
    member,
):

    plan = create_plan(
        db,
        code="pastor_plus",
        profile="pastor_plus",
        entitlements=[
            {
                "key": "sermon.studio"
            }
        ],
    )


    attach_subscription(
        db,
        user=member,
        plan=plan,
    )


    result = check_feature_gate(
        db,
        member,
        "sermon.studio",
    )


    assert result.allowed is True

    assert (
        result.reason
        ==
        "entitlement_granted"
    )


def test_feature_gate_denies_unknown_feature(
    db,
    member,
):

    result = check_feature_gate(
        db,
        member,
        "enterprise.analytics",
    )


    assert result.allowed is False

    assert (
        result.reason
        ==
        "missing_entitlement"
    )
