"""
Tests for read-only XynaFaith V2 usage/quota visibility.
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db.database import Base
from api.models.church import Church
from api.models.plan import Plan
from api.models.subscription import Subscription
from api.models.usage_bucket import UsageBucket
from api.models.user import User
from api.services.entitlement_service import (
    EffectiveAccess,
    EffectiveEntitlement,
)
from api.services.usage_visibility_service import (
    UsageVisibilityConfigurationError,
    UsageVisibilityDenied,
    get_usage_visibility,
)


NOW = datetime(2026, 9, 13, 12, 0, 0)


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
            Church.__table__,
            User.__table__,
            Plan.__table__,
            Subscription.__table__,
            UsageBucket.__table__,
        ],
    )

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def user(db):
    row = User(
        name="Usage Visibility User",
        email="usage-visibility@example.test",
        password="not-a-real-password",
        role="member",
        is_verified=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _grant(
    *,
    limit=30,
    period="monthly",
    source="baseline:free_member",
):
    return EffectiveEntitlement(
        entitlement_key="xyniva.chat",
        enabled=True,
        usage_limit=limit,
        usage_period=period,
        source=source,
    )


def _access(grant=None, *, church_id=None):
    entitlements = {}

    if grant is not None:
        entitlements[grant.entitlement_key] = grant

    return EffectiveAccess(
        baseline_profile="free_member",
        entitlements=entitlements,
        church_id=church_id,
    )


def test_no_bucket_returns_zero_usage_without_creating_bucket(db, user):
    with patch(
        "api.services.usage_visibility_service.resolve_effective_access",
        return_value=_access(_grant()),
    ):
        result = get_usage_visibility(
            db,
            user=user,
            entitlement_key="xyniva.chat",
            metric="conversation_turn",
            now=NOW,
        )

    assert result.quota_owner_type == "user"
    assert result.quota_owner_id == user.id
    assert result.allowance_units == 30
    assert result.consumed_units == 0
    assert result.reserved_units == 0
    assert result.available_units == 30
    assert result.period_start == datetime(2026, 9, 1)
    assert result.period_end == datetime(2026, 10, 1)
    assert result.source == "baseline:free_member"

    assert db.query(UsageBucket).count() == 0


def test_existing_user_bucket_is_authoritative(db, user):
    bucket = UsageBucket(
        user_id=user.id,
        church_id=None,
        entitlement_key="xyniva.chat",
        metric="conversation_turn",
        period_start=datetime(2026, 9, 1),
        period_end=datetime(2026, 10, 1),
        allowance_units=40,
        consumed_units=11,
        reserved_units=3,
    )
    db.add(bucket)
    db.commit()

    with patch(
        "api.services.usage_visibility_service.resolve_effective_access",
        return_value=_access(_grant(limit=30)),
    ):
        result = get_usage_visibility(
            db,
            user=user,
            entitlement_key="xyniva.chat",
            metric="conversation_turn",
            now=NOW,
        )

    assert result.allowance_units == 40
    assert result.consumed_units == 11
    assert result.reserved_units == 3
    assert result.available_units == 26

    persisted = db.query(UsageBucket).one()
    assert persisted.allowance_units == 40
    assert persisted.consumed_units == 11
    assert persisted.reserved_units == 3


def test_reserved_usage_reduces_available_units(db, user):
    bucket = UsageBucket(
        user_id=user.id,
        church_id=None,
        entitlement_key="xyniva.chat",
        metric="conversation_turn",
        period_start=datetime(2026, 9, 1),
        period_end=datetime(2026, 10, 1),
        allowance_units=30,
        consumed_units=20,
        reserved_units=4,
    )
    db.add(bucket)
    db.commit()

    with patch(
        "api.services.usage_visibility_service.resolve_effective_access",
        return_value=_access(_grant()),
    ):
        result = get_usage_visibility(
            db,
            user=user,
            entitlement_key="xyniva.chat",
            metric="conversation_turn",
            now=NOW,
        )

    assert result.available_units == 6


def test_user_subscription_uses_subscription_period(db, user):
    plan = Plan(
        code="usage-personal-pro",
        name="Usage Personal Pro",
        access_profile="pastor_pro",
        owner_type="individual",
        is_active=True,
    )
    db.add(plan)
    db.flush()

    subscription = Subscription(
        user_id=user.id,
        church_id=None,
        plan_id=plan.id,
        status="active",
        current_period_start=datetime(2026, 9, 5, 12, 0, 0),
        current_period_end=datetime(2026, 10, 5, 12, 0, 0),
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)

    grant = _grant(
        limit=500,
        source=f"user_subscription:{subscription.id}",
    )

    with patch(
        "api.services.usage_visibility_service.resolve_effective_access",
        return_value=_access(grant),
    ):
        result = get_usage_visibility(
            db,
            user=user,
            entitlement_key="xyniva.chat",
            metric="conversation_turn",
            now=NOW,
        )

    assert result.quota_owner_type == "user"
    assert result.quota_owner_id == user.id
    assert result.allowance_units == 500
    assert result.period_start == datetime(2026, 9, 5, 12, 0, 0)
    assert result.period_end == datetime(2026, 10, 5, 12, 0, 0)


def test_church_subscription_uses_church_bucket(db, user):
    church = Church(
        name="Usage Church",
    )
    db.add(church)
    db.flush()

    plan = Plan(
        code="usage-church-pro",
        name="Usage Church Pro",
        access_profile="church_pro",
        owner_type="church",
        is_active=True,
    )
    db.add(plan)
    db.flush()

    subscription = Subscription(
        user_id=None,
        church_id=church.id,
        plan_id=plan.id,
        status="active",
        current_period_start=datetime(2026, 9, 1),
        current_period_end=datetime(2026, 10, 1),
    )
    db.add(subscription)
    db.flush()

    bucket = UsageBucket(
        user_id=None,
        church_id=church.id,
        entitlement_key="xyniva.chat",
        metric="conversation_turn",
        period_start=datetime(2026, 9, 1),
        period_end=datetime(2026, 10, 1),
        allowance_units=2000,
        consumed_units=120,
        reserved_units=5,
    )
    db.add(bucket)
    db.commit()

    grant = _grant(
        limit=2000,
        source=f"church_subscription:{subscription.id}",
    )

    with patch(
        "api.services.usage_visibility_service.resolve_effective_access",
        return_value=_access(
            grant,
            church_id=church.id,
        ),
    ):
        result = get_usage_visibility(
            db,
            user=user,
            entitlement_key="xyniva.chat",
            metric="conversation_turn",
            church_id=church.id,
            now=NOW,
        )

    assert result.quota_owner_type == "church"
    assert result.quota_owner_id == church.id
    assert result.allowance_units == 2000
    assert result.consumed_units == 120
    assert result.reserved_units == 5
    assert result.available_units == 1875


def test_church_context_does_not_move_baseline_usage_to_church(db, user):
    with patch(
        "api.services.usage_visibility_service.resolve_effective_access",
        return_value=_access(
            _grant(source="baseline:free_member"),
            church_id=77,
        ),
    ):
        result = get_usage_visibility(
            db,
            user=user,
            entitlement_key="xyniva.chat",
            metric="conversation_turn",
            church_id=77,
            now=NOW,
        )

    assert result.quota_owner_type == "user"
    assert result.quota_owner_id == user.id


def test_missing_entitlement_is_denied(db, user):
    with patch(
        "api.services.usage_visibility_service.resolve_effective_access",
        return_value=_access(),
    ):
        with pytest.raises(UsageVisibilityDenied):
            get_usage_visibility(
                db,
                user=user,
                entitlement_key="xyniva.chat",
                metric="conversation_turn",
                now=NOW,
            )


def test_unlimited_entitlement_fails_closed(db, user):
    with patch(
        "api.services.usage_visibility_service.resolve_effective_access",
        return_value=_access(_grant(limit=None)),
    ):
        with pytest.raises(
            UsageVisibilityConfigurationError,
            match="unlimited",
        ):
            get_usage_visibility(
                db,
                user=user,
                entitlement_key="xyniva.chat",
                metric="conversation_turn",
                now=NOW,
            )


def test_partial_subscription_period_fails_closed(db, user):
    plan = Plan(
        code="usage-partial",
        name="Usage Partial",
        access_profile="pastor_pro",
        owner_type="individual",
        is_active=True,
    )
    db.add(plan)
    db.flush()

    subscription = Subscription(
        user_id=user.id,
        church_id=None,
        plan_id=plan.id,
        status="active",
        current_period_start=datetime(2026, 9, 1),
        current_period_end=None,
    )
    db.add(subscription)
    db.commit()

    grant = _grant(
        limit=500,
        source=f"user_subscription:{subscription.id}",
    )

    with patch(
        "api.services.usage_visibility_service.resolve_effective_access",
        return_value=_access(grant),
    ):
        with pytest.raises(
            UsageVisibilityConfigurationError,
            match="incomplete billing period",
        ):
            get_usage_visibility(
                db,
                user=user,
                entitlement_key="xyniva.chat",
                metric="conversation_turn",
                now=NOW,
            )


def test_read_does_not_mutate_existing_bucket(db, user):
    bucket = UsageBucket(
        user_id=user.id,
        church_id=None,
        entitlement_key="xyniva.chat",
        metric="conversation_turn",
        period_start=datetime(2026, 9, 1),
        period_end=datetime(2026, 10, 1),
        allowance_units=30,
        consumed_units=7,
        reserved_units=2,
    )
    db.add(bucket)
    db.commit()

    before = (
        bucket.allowance_units,
        bucket.consumed_units,
        bucket.reserved_units,
        bucket.updated_at,
    )

    with patch(
        "api.services.usage_visibility_service.resolve_effective_access",
        return_value=_access(_grant()),
    ):
        get_usage_visibility(
            db,
            user=user,
            entitlement_key="xyniva.chat",
            metric="conversation_turn",
            now=NOW,
        )

    db.refresh(bucket)

    after = (
        bucket.allowance_units,
        bucket.consumed_units,
        bucket.reserved_units,
        bucket.updated_at,
    )

    assert after == before
    assert not db.new
    assert not db.dirty
    assert not db.deleted
