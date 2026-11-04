"""
Route tests for the XynaFaith V2 effective access API.
"""

from datetime import datetime
from unittest.mock import patch
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException, HTTPException
from fastapi.testclient import TestClient

from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.schemas.access import EffectiveAccessResponse
from api.services.church_membership_service import (
    ChurchMembershipInactive,
    ChurchMembershipNotFound,
)
from api.services.usage_visibility_service import (
    UsageVisibilityConfigurationError,
    UsageVisibilityDenied,
)
from api.v1.access import router as access_router_module


@pytest.fixture()
def app():
    test_app = FastAPI()

    fake_db = MagicMock()
    authenticated_user = SimpleNamespace(
        id=123,
        role="member",
    )

    test_app.dependency_overrides[get_db] = lambda: fake_db
    test_app.dependency_overrides[
        get_current_user
    ] = lambda: authenticated_user

    test_app.include_router(
        access_router_module.router,
        prefix="/api/v1",
    )

    yield test_app

    test_app.dependency_overrides.clear()


@pytest.fixture()
def client(app):
    return TestClient(app)


def _access_response(
    *,
    user_id=123,
    role="member",
    access_profile="free_member",
    source_profile="free_member",
    plan_code=None,
    entitlements=None,
    limits=None,
):
    return EffectiveAccessResponse(
        user_id=user_id,
        role=role,
        access_profile=access_profile,
        source_profile=source_profile,
        plan_code=plan_code,
        entitlements=entitlements or ["xyniva.chat"],
        limits=limits or {},
    )


def test_personal_access_resolves_without_church_context(
    client,
    monkeypatch,
):
    captured = {}

    def fake_get_effective_access(
        db,
        user,
        *,
        church_id=None,
    ):
        captured["db"] = db
        captured["user_id"] = user.id
        captured["church_id"] = church_id
        return _access_response()

    monkeypatch.setattr(
        access_router_module,
        "get_effective_access",
        fake_get_effective_access,
    )

    response = client.get("/api/v1/access/me")

    assert response.status_code == 200
    assert response.json()["user_id"] == 123
    assert response.json()["access_profile"] == "free_member"
    assert response.json()["source_profile"] == "free_member"
    assert response.json()["plan_code"] is None
    assert response.json()["entitlements"] == ["xyniva.chat"]

    assert captured["user_id"] == 123
    assert captured["church_id"] is None


def test_active_church_context_is_validated_before_resolution(
    client,
    monkeypatch,
):
    events = []

    def fake_membership(
        db,
        *,
        church_id,
        user_id,
    ):
        events.append(
            ("membership", church_id, user_id)
        )
        return SimpleNamespace(
            church_id=church_id,
            user_id=user_id,
            status="active",
        )

    def fake_get_effective_access(
        db,
        user,
        *,
        church_id=None,
    ):
        events.append(
            ("access", church_id, user.id)
        )
        return _access_response(
            access_profile="church_pro",
            plan_code="church_pro",
            entitlements=[
                "xyniva.chat",
                "reading_plans",
            ],
        )

    monkeypatch.setattr(
        access_router_module,
        "get_active_church_membership",
        fake_membership,
    )
    monkeypatch.setattr(
        access_router_module,
        "get_effective_access",
        fake_get_effective_access,
    )

    response = client.get(
        "/api/v1/access/me?church_id=77"
    )

    assert response.status_code == 200
    assert response.json()["plan_code"] == "church_pro"

    assert events == [
        ("membership", 77, 123),
        ("access", 77, 123),
    ]


def test_foreign_church_context_returns_404(
    client,
    monkeypatch,
):
    access_called = False

    def fake_membership(db, **kwargs):
        raise ChurchMembershipNotFound()

    def fake_get_effective_access(*args, **kwargs):
        nonlocal access_called
        access_called = True
        return _access_response()

    monkeypatch.setattr(
        access_router_module,
        "get_active_church_membership",
        fake_membership,
    )
    monkeypatch.setattr(
        access_router_module,
        "get_effective_access",
        fake_get_effective_access,
    )

    response = client.get(
        "/api/v1/access/me?church_id=77"
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Church Space not found",
    }
    assert access_called is False


def test_inactive_church_context_returns_403(
    client,
    monkeypatch,
):
    access_called = False

    def fake_membership(db, **kwargs):
        raise ChurchMembershipInactive()

    def fake_get_effective_access(*args, **kwargs):
        nonlocal access_called
        access_called = True
        return _access_response()

    monkeypatch.setattr(
        access_router_module,
        "get_active_church_membership",
        fake_membership,
    )
    monkeypatch.setattr(
        access_router_module,
        "get_effective_access",
        fake_get_effective_access,
    )

    response = client.get(
        "/api/v1/access/me?church_id=77"
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Church membership is not active",
    }
    assert access_called is False


def test_caller_cannot_override_authenticated_user(
    client,
    monkeypatch,
):
    captured = {}

    def fake_get_effective_access(
        db,
        user,
        *,
        church_id=None,
    ):
        captured["user_id"] = user.id
        return _access_response()

    monkeypatch.setattr(
        access_router_module,
        "get_effective_access",
        fake_get_effective_access,
    )

    response = client.get(
        "/api/v1/access/me?user_id=999"
    )

    assert response.status_code == 200
    assert captured["user_id"] == 123
    assert response.json()["user_id"] == 123


@pytest.mark.parametrize(
    "church_id",
    ["0", "-1"],
)
def test_invalid_church_id_is_rejected(
    client,
    church_id,
):
    response = client.get(
        f"/api/v1/access/me?church_id={church_id}"
    )

    assert response.status_code == 422


def test_usage_returns_authenticated_users_quota(client):
    usage = SimpleNamespace(
        entitlement_key="xyniva.chat",
        metric="conversation_turn",
        quota_owner_type="user",
        quota_owner_id=123,
        allowance_units=30,
        consumed_units=8,
        reserved_units=2,
        available_units=20,
        period_start=datetime(2026, 9, 1),
        period_end=datetime(2026, 10, 1),
        source="baseline:free_member",
    )

    with patch(
        "api.v1.access.router.get_usage_visibility",
        return_value=usage,
    ) as usage_mock:
        response = client.get("/api/v1/access/usage")

    assert response.status_code == 200
    assert response.json() == {
        "entitlement_key": "xyniva.chat",
        "metric": "conversation_turn",
        "quota_scope": "user",
        "allowance_units": 30,
        "consumed_units": 8,
        "reserved_units": 2,
        "available_units": 20,
        "period_start": "2026-09-01T00:00:00",
        "period_end": "2026-10-01T00:00:00",
    }

    kwargs = usage_mock.call_args.kwargs
    assert kwargs["user"].id == 123
    assert kwargs["church_id"] is None
    assert kwargs["entitlement_key"] == "xyniva.chat"
    assert kwargs["metric"] == "conversation_turn"


def test_usage_active_church_is_validated_before_resolution(client):
    events = []

    def validate(*args, **kwargs):
        events.append(
            (
                "membership",
                kwargs["church_id"],
                kwargs["user_id"],
            )
        )

    def resolve(*args, **kwargs):
        events.append(
            (
                "usage",
                kwargs["church_id"],
                kwargs["user"].id,
            )
        )

        return SimpleNamespace(
            entitlement_key="xyniva.chat",
            metric="conversation_turn",
            quota_owner_type="church",
            quota_owner_id=44,
            allowance_units=2000,
            consumed_units=120,
            reserved_units=5,
            available_units=1875,
            period_start=datetime(2026, 9, 1),
            period_end=datetime(2026, 10, 1),
            source="church_subscription:52",
        )

    with (
        patch(
            "api.v1.access.router._validate_church_context",
            side_effect=validate,
        ),
        patch(
            "api.v1.access.router.get_usage_visibility",
            side_effect=resolve,
        ),
    ):
        response = client.get(
            "/api/v1/access/usage?church_id=44"
        )

    assert response.status_code == 200
    assert events == [
        ("membership", 44, 123),
        ("usage", 44, 123),
    ]
    assert response.json()["quota_scope"] == "church"
    assert "quota_owner_id" not in response.json()
    assert "source" not in response.json()


def test_usage_foreign_church_returns_404_before_resolution(client):
    with (
        patch(
            "api.v1.access.router._validate_church_context",
            side_effect=HTTPException(
                status_code=404,
                detail="Church Space not found",
            ),
        ),
        patch(
            "api.v1.access.router.get_usage_visibility",
        ) as usage_mock,
    ):
        response = client.get(
            "/api/v1/access/usage?church_id=999"
        )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Church Space not found"
    }
    usage_mock.assert_not_called()


def test_usage_inactive_church_returns_403_before_resolution(client):
    with (
        patch(
            "api.v1.access.router._validate_church_context",
            side_effect=HTTPException(
                status_code=403,
                detail="Church membership is not active",
            ),
        ),
        patch(
            "api.v1.access.router.get_usage_visibility",
        ) as usage_mock,
    ):
        response = client.get(
            "/api/v1/access/usage?church_id=44"
        )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Church membership is not active"
    }
    usage_mock.assert_not_called()


def test_usage_missing_entitlement_returns_403(client):
    with patch(
        "api.v1.access.router.get_usage_visibility",
        side_effect=UsageVisibilityDenied(
            "Missing entitlement: xyniva.chat"
        ),
    ):
        response = client.get("/api/v1/access/usage")

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Xyniva Chat is not available"
    }


def test_usage_configuration_error_returns_409(client):
    with patch(
        "api.v1.access.router.get_usage_visibility",
        side_effect=UsageVisibilityConfigurationError(
            "xyniva.chat is unlimited and has no numeric quota"
        ),
    ):
        response = client.get("/api/v1/access/usage")

    assert response.status_code == 409
    assert response.json() == {
        "detail": (
            "Xyniva Chat usage is not available "
            "for this access configuration"
        )
    }


def test_usage_caller_cannot_override_authenticated_user(client):
    usage = SimpleNamespace(
        entitlement_key="xyniva.chat",
        metric="conversation_turn",
        quota_owner_type="user",
        quota_owner_id=123,
        allowance_units=30,
        consumed_units=0,
        reserved_units=0,
        available_units=30,
        period_start=datetime(2026, 9, 1),
        period_end=datetime(2026, 10, 1),
        source="baseline:free_member",
    )

    with patch(
        "api.v1.access.router.get_usage_visibility",
        return_value=usage,
    ) as usage_mock:
        response = client.get(
            "/api/v1/access/usage?user_id=999"
        )

    assert response.status_code == 200

    kwargs = usage_mock.call_args.kwargs
    assert kwargs["user"].id == 123
    assert kwargs["church_id"] is None


@pytest.mark.parametrize("church_id", ["0", "-1"])
def test_usage_invalid_church_id_is_rejected(client, church_id):
    with patch(
        "api.v1.access.router.get_usage_visibility",
    ) as usage_mock:
        response = client.get(
            f"/api/v1/access/usage?church_id={church_id}"
        )

    assert response.status_code == 422
    usage_mock.assert_not_called()
