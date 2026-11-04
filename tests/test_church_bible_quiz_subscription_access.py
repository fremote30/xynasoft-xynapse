"""Bible Quiz subscription and quota-source integration tests."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db.database import Base
from api.models.user import User
from api.models.church import Church
from api.models.church_membership import ChurchMembership
from api.models.plan import Plan
from api.models.plan_entitlement import PlanEntitlement
from api.models.subscription import Subscription
from api.core.entitlements import (
    ENTITLEMENT_BIBLE_QUIZZES,
    ENTITLEMENT_BIBLE_QUIZZES_AUTHOR,
    ENTITLEMENT_BIBLE_QUIZZES_AI,
)
from api.core.product_catalog import (
    PLAN_CODE_PASTOR_PRO,
    PLAN_CODE_CHURCH,
    PLAN_CODE_CHURCH_PRO,
)
from api.services.product_catalog_sync import sync_product_catalog
from api.services.entitlement_service import resolve_effective_access


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(
        engine,
        tables=[
            User.__table__,
            Church.__table__,
            ChurchMembership.__table__,
            Plan.__table__,
            PlanEntitlement.__table__,
            Subscription.__table__,
        ],
    )
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        sync_product_catalog(session)
        session.commit()
        yield session
    finally:
        session.close()
        engine.dispose()


def make_user(db, name, role="pastor"):
    user = User(
        name=name,
        email=f"{name.lower().replace(' ', '_')}@quiz.test",
        password="test-password",
        role=role,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_church(db, name, owner):
    church = Church(
        name=name,
        location="Accra",
        country="Ghana",
        city="Accra",
    )
    db.add(church)
    db.commit()
    db.refresh(church)
    return church


def add_membership(db, user, church, status="active"):
    membership = ChurchMembership(
        user_id=user.id,
        church_id=church.id,
        role="member",
        status=status,
    )
    db.add(membership)
    db.commit()
    return membership


def subscribe(db, code, *, user=None, church=None,
              status="active", expired=False):
    plan = db.query(Plan).filter(Plan.code == code).one()
    now = datetime.utcnow()
    subscription = Subscription(
        plan_id=plan.id,
        user_id=user.id if user else None,
        church_id=church.id if church else None,
        status=status,
        starts_at=now - timedelta(days=30),
        current_period_start=now - timedelta(days=1),
        current_period_end=(
            now - timedelta(seconds=1)
            if expired else now + timedelta(days=29)
        ),
    )
    db.add(subscription)
    db.commit()
    return subscription


def grant(db, user, key, church_id=None):
    return resolve_effective_access(
        db, user=user, church_id=church_id
    ).get(key)


def test_free_member_can_participate_but_not_author_or_generate(db):
    member = make_user(db, "Free Member", role="member")
    assert grant(db, member, ENTITLEMENT_BIBLE_QUIZZES)
    assert grant(db, member, ENTITLEMENT_BIBLE_QUIZZES_AUTHOR) is None
    assert grant(db, member, ENTITLEMENT_BIBLE_QUIZZES_AI) is None


def test_free_pastor_has_ten_monthly_ai_quizzes(db):
    pastor = make_user(db, "Free Pastor")
    assert grant(db, pastor, ENTITLEMENT_BIBLE_QUIZZES_AUTHOR)
    ai = grant(db, pastor, ENTITLEMENT_BIBLE_QUIZZES_AI)
    assert ai is not None
    assert ai.usage_limit == 10
    assert ai.usage_period == "monthly"
    assert ai.source.startswith("baseline:")


def test_pastor_pro_has_one_hundred_monthly_ai_quizzes(db):
    pastor = make_user(db, "Paid Pastor")
    subscribe(db, PLAN_CODE_PASTOR_PRO, user=pastor)
    ai = grant(db, pastor, ENTITLEMENT_BIBLE_QUIZZES_AI)
    assert ai is not None
    assert ai.usage_limit == 100
    assert ai.usage_period == "monthly"
    assert ai.source.startswith("user_subscription:")
    assert grant(db, pastor, ENTITLEMENT_BIBLE_QUIZZES_AUTHOR)


def test_expired_pastor_pro_falls_back_to_ten(db):
    pastor = make_user(db, "Expired Pastor")
    subscribe(db, PLAN_CODE_PASTOR_PRO, user=pastor, expired=True)
    ai = grant(db, pastor, ENTITLEMENT_BIBLE_QUIZZES_AI)
    assert ai.usage_limit == 10
    assert ai.source.startswith("baseline:")


def test_suspended_pastor_pro_falls_back_to_ten(db):
    pastor = make_user(db, "Suspended Pastor")
    subscribe(
        db, PLAN_CODE_PASTOR_PRO, user=pastor, status="suspended"
    )
    ai = grant(db, pastor, ENTITLEMENT_BIBLE_QUIZZES_AI)
    assert ai.usage_limit == 10


def test_church_plan_does_not_grant_ai_to_member(db):
    owner = make_user(db, "Church Owner")
    member = make_user(db, "Church Member", role="member")
    church = make_church(db, "Church Basic", owner)
    add_membership(db, member, church)
    subscribe(db, PLAN_CODE_CHURCH, church=church)
    assert grant(db, member, ENTITLEMENT_BIBLE_QUIZZES_AUTHOR, church.id)
    assert grant(db, member, ENTITLEMENT_BIBLE_QUIZZES_AI, church.id) is None


def test_church_pro_ai_is_inherited_only_by_active_member(db):
    owner = make_user(db, "Pro Owner")
    member = make_user(db, "Pro Member", role="member")
    outsider = make_user(db, "Pro Outsider", role="member")
    church = make_church(db, "Church Premium", owner)
    add_membership(db, member, church)
    subscribe(db, PLAN_CODE_CHURCH_PRO, church=church)
    ai = grant(db, member, ENTITLEMENT_BIBLE_QUIZZES_AI, church.id)
    assert ai is not None
    assert ai.source.startswith("church_subscription:")
    assert grant(db, outsider, ENTITLEMENT_BIBLE_QUIZZES_AI, church.id) is None
    assert grant(db, member, ENTITLEMENT_BIBLE_QUIZZES_AI) is None


def test_suspended_church_membership_cannot_inherit_church_ai(db):
    owner = make_user(db, "Suspension Owner")
    member = make_user(db, "Suspension Member", role="member")
    church = make_church(db, "Suspension Church", owner)
    add_membership(db, member, church, status="suspended")
    subscribe(db, PLAN_CODE_CHURCH_PRO, church=church)
    assert grant(db, member, ENTITLEMENT_BIBLE_QUIZZES_AI, church.id) is None


def test_free_pastor_allowance_is_not_multiplied_by_churches(db):
    pastor = make_user(db, "Multi Church Pastor")
    first = make_church(db, "First Quiz Church", pastor)
    second = make_church(db, "Second Quiz Church", pastor)
    add_membership(db, pastor, first)
    add_membership(db, pastor, second)

    first_grant = grant(db, pastor, ENTITLEMENT_BIBLE_QUIZZES_AI, first.id)
    second_grant = grant(db, pastor, ENTITLEMENT_BIBLE_QUIZZES_AI, second.id)

    assert first_grant.usage_limit == 10
    assert second_grant.usage_limit == 10
    assert first_grant.source.startswith("baseline:")
    assert second_grant.source.startswith("baseline:")


def test_church_pro_entitlement_does_not_cross_tenants(db):
    owner = make_user(db, "Tenant Owner")
    member = make_user(db, "Tenant Member", role="member")
    first = make_church(db, "Paid Quiz Church", owner)
    second = make_church(db, "Unpaid Quiz Church", owner)
    add_membership(db, member, first)
    add_membership(db, member, second)
    subscribe(db, PLAN_CODE_CHURCH_PRO, church=first)

    paid = grant(db, member, ENTITLEMENT_BIBLE_QUIZZES_AI, first.id)
    unpaid = grant(db, member, ENTITLEMENT_BIBLE_QUIZZES_AI, second.id)

    assert paid is not None
    assert paid.source.startswith("church_subscription:")
    assert unpaid is None
