"""
Route-boundary tests for XynaFaith V2 Church Space authorization.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from api.core.church_dependencies import (
    require_church_permission_dependency,
)
from api.core.church_rbac import (
    PERMISSION_MEMBERS_MANAGE,
)
from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.services.church_membership_service import (
    ChurchMembershipInactive,
    ChurchMembershipNotFound,
    ChurchPermissionDenied,
)


@pytest.fixture()
def app():
    test_app = FastAPI()

    fake_db = MagicMock()
    authenticated_user = SimpleNamespace(
        id=123,
        role="admin",
    )

    test_app.dependency_overrides[get_db] = lambda: fake_db
    test_app.dependency_overrides[
        get_current_user
    ] = lambda: authenticated_user

    @test_app.get("/churches/{church_id}/members")
    def protected_route(
        church_id: int,
        membership=Depends(
            require_church_permission_dependency(
                PERMISSION_MEMBERS_MANAGE
            )
        ),
    ):
        return {
            "church_id": membership.church_id,
            "user_id": membership.user_id,
            "role": membership.role,
        }

    yield test_app

    test_app.dependency_overrides.clear()


@pytest.fixture()
def client(app):
    return TestClient(app)


def test_authorized_membership_is_returned(
    client,
    monkeypatch,
):
    captured = {}

    def fake_require(
        db,
        *,
        church_id,
        user_id,
        permission,
    ):
        captured["db"] = db
        captured["church_id"] = church_id
        captured["user_id"] = user_id
        captured["permission"] = permission

        return SimpleNamespace(
            church_id=church_id,
            user_id=user_id,
            role="admin",
        )

    monkeypatch.setattr(
        "api.core.church_dependencies.require_church_permission",
        fake_require,
    )

    response = client.get(
        "/churches/77/members",
    )

    assert response.status_code == 200
    assert response.json() == {
        "church_id": 77,
        "user_id": 123,
        "role": "admin",
    }

    assert captured["church_id"] == 77
    assert captured["user_id"] == 123
    assert (
        captured["permission"]
        == PERMISSION_MEMBERS_MANAGE
    )


def test_user_identity_cannot_be_supplied_by_caller(
    client,
    monkeypatch,
):
    captured = {}

    def fake_require(
        db,
        *,
        church_id,
        user_id,
        permission,
    ):
        captured["user_id"] = user_id

        return SimpleNamespace(
            church_id=church_id,
            user_id=user_id,
            role="admin",
        )

    monkeypatch.setattr(
        "api.core.church_dependencies.require_church_permission",
        fake_require,
    )

    response = client.get(
        "/churches/77/members?user_id=999",
    )

    assert response.status_code == 200

    # Authentication remains authoritative.
    assert captured["user_id"] == 123


def test_missing_membership_returns_404(
    client,
    monkeypatch,
):
    def fake_require(db, **kwargs):
        raise ChurchMembershipNotFound(
            "membership not found"
        )

    monkeypatch.setattr(
        "api.core.church_dependencies.require_church_permission",
        fake_require,
    )

    response = client.get(
        "/churches/77/members",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Church Space not found",
    }


def test_inactive_membership_returns_403(
    client,
    monkeypatch,
):
    def fake_require(db, **kwargs):
        raise ChurchMembershipInactive(
            "membership inactive"
        )

    monkeypatch.setattr(
        "api.core.church_dependencies.require_church_permission",
        fake_require,
    )

    response = client.get(
        "/churches/77/members",
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Church membership is not active",
    }


def test_insufficient_permission_returns_403(
    client,
    monkeypatch,
):
    def fake_require(db, **kwargs):
        raise ChurchPermissionDenied(
            "permission denied"
        )

    monkeypatch.setattr(
        "api.core.church_dependencies.require_church_permission",
        fake_require,
    )

    response = client.get(
        "/churches/77/members",
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Insufficient Church Space permission",
    }
