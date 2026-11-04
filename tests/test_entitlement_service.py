from datetime import datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db.database import Base
from api.models.church import Church
from api.models.church_membership import ChurchMembership
from api.models.plan import Plan
from api.models.plan_entitlement import PlanEntitlement
from api.models.subscription import Subscription
from api.models.user import User
from api.services.entitlement_service import resolve_effective_access


def _db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    for table in (
        Church.__table__,
        User.__table__,
        ChurchMembership.__table__,
        Plan.__table__,
        PlanEntitlement.__table__,
        Subscription.__table__,
    ):
        table.create(engine, checkfirst=True)

    Session = sessionmaker(bind=engine)
    return Session()


def _user(db, *, role="member"):
    church = Church(name="Resolver Church")
    db.add(church)
    db.flush()

    user = User(
        name="Resolver User",
        email=f"resolver-{role}@example.com",
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user, church


def _plan(
    db,
    *,
    code,
    owner_type,
    access_profile,
    entitlement_key,
    usage_limit=None,
):
    plan = Plan(
        code=code,
        name=code,
        access_profile=access_profile,
        owner_type=owner_type,
        is_active=True,
    )
    db.add(plan)
    db.flush()

    db.add(
        PlanEntitlement(
            plan_id=plan.id,
            entitlement_key=entitlement_key,
            enabled=True,
            usage_limit=usage_limit,
            usage_period="monthly" if usage_limit else None,
        )
    )

    db.commit()
    db.refresh(plan)

    return plan


def test_member_receives_free_xyniva_baseline():
    db = _db()
    user, _ = _user(db)

    access = resolve_effective_access(
        db,
        user=user,
    )

    assert access.has("xyniva.chat")
    assert access.get("xyniva.chat").usage_limit == 30


def test_pastor_receives_larger_free_xyniva_baseline():
    db = _db()
    user, _ = _user(db, role="pastor")

    access = resolve_effective_access(
        db,
        user=user,
    )

    assert access.has("xyniva.chat")
    assert access.get("xyniva.chat").usage_limit == 75
    assert access.has("sermon.studio")


def test_individual_subscription_expands_access():
    db = _db()
    user, _ = _user(db, role="pastor")

    plan = _plan(
        db,
        code="pastor-pro-test",
        owner_type="individual",
        access_profile="pastor_pro",
        entitlement_key="biblical_research",
    )

    subscription = Subscription(
        plan_id=plan.id,
        user_id=user.id,
        status="active",
    )
    db.add(subscription)
    db.commit()

    access = resolve_effective_access(
        db,
        user=user,
    )

    assert access.has("biblical_research")
    assert access.user_subscription_id == subscription.id


def test_paid_higher_limit_replaces_lower_baseline_limit():
    db = _db()
    user, _ = _user(db, role="pastor")

    plan = _plan(
        db,
        code="pastor-pro-limit-test",
        owner_type="individual",
        access_profile="pastor_pro",
        entitlement_key="xyniva.chat",
        usage_limit=500,
    )

    db.add(
        Subscription(
            plan_id=plan.id,
            user_id=user.id,
            status="active",
        )
    )
    db.commit()

    access = resolve_effective_access(
        db,
        user=user,
    )

    assert access.get("xyniva.chat").usage_limit == 500


def test_unlimited_paid_grant_beats_numeric_baseline():
    db = _db()
    user, _ = _user(db, role="pastor")

    plan = _plan(
        db,
        code="pastor-pro-unlimited-test",
        owner_type="individual",
        access_profile="pastor_pro",
        entitlement_key="xyniva.chat",
        usage_limit=None,
    )

    db.add(
        Subscription(
            plan_id=plan.id,
            user_id=user.id,
            status="active",
        )
    )
    db.commit()

    access = resolve_effective_access(
        db,
        user=user,
    )

    assert access.get("xyniva.chat").usage_limit is None


def test_expired_subscription_does_not_expand_access():
    db = _db()
    user, _ = _user(db)

    plan = _plan(
        db,
        code="expired-test",
        owner_type="individual",
        access_profile="pastor_pro",
        entitlement_key="biblical_research",
    )

    now = datetime.utcnow()

    db.add(
        Subscription(
            plan_id=plan.id,
            user_id=user.id,
            status="active",
            starts_at=now - timedelta(days=60),
            current_period_end=now - timedelta(days=1),
        )
    )
    db.commit()

    access = resolve_effective_access(
        db,
        user=user,
        now=now,
    )

    assert not access.has("biblical_research")


def test_church_subscription_requires_active_membership():
    db = _db()
    user, church = _user(db)

    plan = _plan(
        db,
        code="church-test",
        owner_type="church",
        access_profile="church",
        entitlement_key="church.pastoral_care",
    )

    db.add(
        Subscription(
            plan_id=plan.id,
            church_id=church.id,
            status="active",
        )
    )
    db.commit()

    access = resolve_effective_access(
        db,
        user=user,
        church_id=church.id,
    )

    assert not access.has("church.pastoral_care")
    assert access.church_subscription_id is None


def test_active_member_inherits_church_subscription():
    db = _db()
    user, church = _user(db)

    db.add(
        ChurchMembership(
            church_id=church.id,
            user_id=user.id,
            role="member",
            status="active",
            is_primary=True,
        )
    )
    db.commit()

    plan = _plan(
        db,
        code="church-active-test",
        owner_type="church",
        access_profile="church",
        entitlement_key="church.pastoral_care",
    )

    subscription = Subscription(
        plan_id=plan.id,
        church_id=church.id,
        status="active",
    )
    db.add(subscription)
    db.commit()

    access = resolve_effective_access(
        db,
        user=user,
        church_id=church.id,
    )

    assert access.has("church.pastoral_care")
    assert access.church_subscription_id == subscription.id


def test_church_entitlements_do_not_leak_across_tenants():
    db = _db()

    church_a = Church(name="Church A")
    church_b = Church(name="Church B")
    db.add_all([church_a, church_b])
    db.flush()

    user = User(
        name="Tenant User",
        email="tenant-entitlement@example.com",
        role="member",
    )
    db.add(user)
    db.flush()

    db.add_all(
        [
            ChurchMembership(
                church_id=church_a.id,
                user_id=user.id,
                role="member",
                status="active",
                is_primary=True,
            ),
            ChurchMembership(
                church_id=church_b.id,
                user_id=user.id,
                role="member",
                status="active",
                is_primary=False,
            ),
        ]
    )

    plan = Plan(
        code="church-a-pro",
        name="Church A Pro",
        access_profile="church_pro",
        owner_type="church",
        is_active=True,
    )
    db.add(plan)
    db.flush()

    db.add(
        PlanEntitlement(
            plan_id=plan.id,
            entitlement_key="church.intelligence",
            enabled=True,
        )
    )

    db.add(
        Subscription(
            plan_id=plan.id,
            church_id=church_a.id,
            status="active",
        )
    )

    db.commit()

    access_a = resolve_effective_access(
        db,
        user=user,
        church_id=church_a.id,
    )

    access_b = resolve_effective_access(
        db,
        user=user,
        church_id=church_b.id,
    )

    assert access_a.has("church.intelligence")
    assert not access_b.has("church.intelligence")


def test_global_admin_role_does_not_bypass_church_membership():
    db = _db()
    user, church = _user(db, role="admin")

    plan = _plan(
        db,
        code="admin-bypass-test",
        owner_type="church",
        access_profile="church",
        entitlement_key="church.intelligence",
    )

    db.add(
        Subscription(
            plan_id=plan.id,
            church_id=church.id,
            status="active",
        )
    )
    db.commit()

    access = resolve_effective_access(
        db,
        user=user,
        church_id=church.id,
    )

    assert not access.has("church.intelligence")
