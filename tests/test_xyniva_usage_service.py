from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from api.services.ai_usage_metering import UsagePeriod
from api.services.entitlement_service import (
    EffectiveAccess,
    EffectiveEntitlement,
)
from api.services.xyniva_usage_service import (
    XynivaUsageConfigurationError,
    XynivaUsageDenied,
    complete_xyniva_usage,
    release_xyniva_usage,
    reserve_xyniva_usage,
)


def _user(*, user_id=7, role="member"):
    return SimpleNamespace(
        id=user_id,
        role=role,
    )


def _access(
    grant=None,
    *,
    profile="free_member",
    church_id=None,
):
    entitlements = {}

    if grant is not None:
        entitlements[grant.entitlement_key] = grant

    return EffectiveAccess(
        baseline_profile=profile,
        entitlements=entitlements,
        church_id=church_id,
    )


def _grant(
    *,
    key="xyniva.chat",
    limit=30,
    period="monthly",
    source="baseline:free_member",
):
    return EffectiveEntitlement(
        entitlement_key=key,
        enabled=True,
        usage_limit=limit,
        usage_period=period,
        source=source,
    )


def test_missing_entitlement_is_denied():
    db = Mock()
    user = _user()

    with patch(
        "api.services.xyniva_usage_service.resolve_effective_access",
        return_value=_access(),
    ):
        with pytest.raises(XynivaUsageDenied):
            reserve_xyniva_usage(
                db,
                user=user,
                request_id="missing-1",
                entitlement_key="does.not.exist",
            )


def test_free_member_uses_user_bucket_and_baseline_limit():
    db = Mock()
    user = _user()

    with (
        patch(
            "api.services.xyniva_usage_service.resolve_effective_access",
            return_value=_access(_grant()),
        ),
        patch(
            "api.services.xyniva_usage_service.reserve_usage",
            return_value=SimpleNamespace(request_id="free-1"),
        ) as reserve_mock,
    ):
        result = reserve_xyniva_usage(
            db,
            user=user,
            request_id="free-1",
        )

    assert result.request_id == "free-1"

    kwargs = reserve_mock.call_args.kwargs

    assert kwargs["actor_user_id"] == 7
    assert kwargs["quota_user_id"] == 7
    assert kwargs["quota_church_id"] is None
    assert kwargs["subscription_id"] is None
    assert kwargs["allowance_units"] == 30
    assert kwargs["usage_period"] == "monthly"
    assert kwargs["units"] == 1
    assert kwargs["explicit_period"] is None


def test_user_subscription_uses_subscription_period():
    db = Mock()
    user = _user()

    start = datetime(2026, 9, 5, 12, 0, 0)
    end = datetime(2026, 10, 5, 12, 0, 0)

    subscription = SimpleNamespace(
        current_period_start=start,
        current_period_end=end,
    )

    db.query.return_value.filter.return_value.one_or_none.return_value = (
        subscription
    )

    grant = _grant(
        limit=500,
        source="user_subscription:41",
    )

    with (
        patch(
            "api.services.xyniva_usage_service.resolve_effective_access",
            return_value=_access(grant),
        ),
        patch(
            "api.services.xyniva_usage_service.reserve_usage",
            return_value=SimpleNamespace(request_id="paid-1"),
        ) as reserve_mock,
    ):
        reserve_xyniva_usage(
            db,
            user=user,
            request_id="paid-1",
        )

    kwargs = reserve_mock.call_args.kwargs

    assert kwargs["quota_user_id"] == 7
    assert kwargs["quota_church_id"] is None
    assert kwargs["subscription_id"] == 41
    assert kwargs["allowance_units"] == 500
    assert kwargs["explicit_period"] == UsagePeriod(
        start=start,
        end=end,
    )


def test_church_subscription_uses_church_bucket():
    db = Mock()
    user = _user()

    start = datetime(2026, 9, 1, 0, 0, 0)
    end = datetime(2026, 10, 1, 0, 0, 0)

    subscription = SimpleNamespace(
        current_period_start=start,
        current_period_end=end,
    )

    db.query.return_value.filter.return_value.one_or_none.return_value = (
        subscription
    )

    grant = _grant(
        limit=2000,
        source="church_subscription:52",
    )

    with (
        patch(
            "api.services.xyniva_usage_service.resolve_effective_access",
            return_value=_access(
                grant,
                church_id=12,
            ),
        ),
        patch(
            "api.services.xyniva_usage_service.reserve_usage",
            return_value=SimpleNamespace(request_id="church-1"),
        ) as reserve_mock,
    ):
        reserve_xyniva_usage(
            db,
            user=user,
            request_id="church-1",
            church_id=12,
        )

    kwargs = reserve_mock.call_args.kwargs

    assert kwargs["actor_user_id"] == 7
    assert kwargs["quota_user_id"] is None
    assert kwargs["quota_church_id"] == 12
    assert kwargs["subscription_id"] == 52
    assert kwargs["allowance_units"] == 2000
    assert kwargs["explicit_period"] == UsagePeriod(
        start=start,
        end=end,
    )


def test_unlimited_entitlement_does_not_use_numeric_sentinel():
    db = Mock()
    user = _user()

    grant = _grant(
        limit=None,
        source="user_subscription:41",
    )

    with (
        patch(
            "api.services.xyniva_usage_service.resolve_effective_access",
            return_value=_access(grant),
        ),
        patch(
            "api.services.xyniva_usage_service.reserve_usage",
        ) as reserve_mock,
    ):
        with pytest.raises(XynivaUsageConfigurationError):
            reserve_xyniva_usage(
                db,
                user=user,
                request_id="unlimited-1",
            )

    reserve_mock.assert_not_called()


def test_complete_delegates_to_atomic_metering():
    db = Mock()

    with patch(
        "api.services.xyniva_usage_service.complete_usage",
        return_value="completed",
    ) as complete_mock:
        result = complete_xyniva_usage(
            db,
            request_id="complete-1",
        )

    assert result == "completed"
    complete_mock.assert_called_once_with(
        db,
        request_id="complete-1",
        now=None,
    )


def test_release_delegates_to_atomic_metering():
    db = Mock()

    with patch(
        "api.services.xyniva_usage_service.release_usage",
        return_value="released",
    ) as release_mock:
        result = release_xyniva_usage(
            db,
            request_id="release-1",
        )

    assert result == "released"
    release_mock.assert_called_once_with(
        db,
        request_id="release-1",
        now=None,
    )


def test_church_context_does_not_move_baseline_usage_to_church():
    """
    Church context is authorization/context only.

    If the winning entitlement is still the user's baseline grant,
    usage must remain on the user's quota bucket.
    """
    db = Mock()
    user = _user()

    grant = _grant(
        limit=30,
        source="baseline:free_member",
    )

    with (
        patch(
            "api.services.xyniva_usage_service.resolve_effective_access",
            return_value=_access(
                grant,
                church_id=12,
            ),
        ),
        patch(
            "api.services.xyniva_usage_service.reserve_usage",
            return_value=SimpleNamespace(request_id="baseline-church-1"),
        ) as reserve_mock,
    ):
        reserve_xyniva_usage(
            db,
            user=user,
            request_id="baseline-church-1",
            church_id=12,
        )

    kwargs = reserve_mock.call_args.kwargs

    assert kwargs["quota_user_id"] == 7
    assert kwargs["quota_church_id"] is None
    assert kwargs["subscription_id"] is None
    assert kwargs["allowance_units"] == 30


def test_winning_user_subscription_stays_user_owned_in_church_context():
    """
    A Church context must not override the source of the entitlement
    that actually won composition.
    """
    db = Mock()
    user = _user()

    start = datetime(2026, 9, 10, 0, 0, 0)
    end = datetime(2026, 10, 10, 0, 0, 0)

    subscription = SimpleNamespace(
        current_period_start=start,
        current_period_end=end,
    )

    db.query.return_value.filter.return_value.one_or_none.return_value = (
        subscription
    )

    grant = _grant(
        limit=500,
        source="user_subscription:61",
    )

    with (
        patch(
            "api.services.xyniva_usage_service.resolve_effective_access",
            return_value=_access(
                grant,
                church_id=12,
            ),
        ),
        patch(
            "api.services.xyniva_usage_service.reserve_usage",
            return_value=SimpleNamespace(request_id="user-in-church-1"),
        ) as reserve_mock,
    ):
        reserve_xyniva_usage(
            db,
            user=user,
            request_id="user-in-church-1",
            church_id=12,
        )

    kwargs = reserve_mock.call_args.kwargs

    assert kwargs["quota_user_id"] == 7
    assert kwargs["quota_church_id"] is None
    assert kwargs["subscription_id"] == 61
    assert kwargs["allowance_units"] == 500


def test_partial_subscription_billing_period_fails_closed():
    db = Mock()
    user = _user()

    subscription = SimpleNamespace(
        current_period_start=datetime(2026, 9, 1, 0, 0, 0),
        current_period_end=None,
    )

    db.query.return_value.filter.return_value.one_or_none.return_value = (
        subscription
    )

    grant = _grant(
        limit=500,
        source="user_subscription:71",
    )

    with (
        patch(
            "api.services.xyniva_usage_service.resolve_effective_access",
            return_value=_access(grant),
        ),
        patch(
            "api.services.xyniva_usage_service.reserve_usage",
        ) as reserve_mock,
    ):
        with pytest.raises(
            XynivaUsageConfigurationError,
            match="incomplete billing period",
        ):
            reserve_xyniva_usage(
                db,
                user=user,
                request_id="partial-period-1",
            )

    reserve_mock.assert_not_called()


def test_reversed_subscription_billing_period_fails_closed():
    db = Mock()
    user = _user()

    subscription = SimpleNamespace(
        current_period_start=datetime(2026, 10, 1, 0, 0, 0),
        current_period_end=datetime(2026, 9, 1, 0, 0, 0),
    )

    db.query.return_value.filter.return_value.one_or_none.return_value = (
        subscription
    )

    grant = _grant(
        limit=500,
        source="user_subscription:72",
    )

    with (
        patch(
            "api.services.xyniva_usage_service.resolve_effective_access",
            return_value=_access(grant),
        ),
        patch(
            "api.services.xyniva_usage_service.reserve_usage",
        ) as reserve_mock,
    ):
        with pytest.raises(
            XynivaUsageConfigurationError,
            match="invalid billing period",
        ):
            reserve_xyniva_usage(
                db,
                user=user,
                request_id="reversed-period-1",
            )

    reserve_mock.assert_not_called()
