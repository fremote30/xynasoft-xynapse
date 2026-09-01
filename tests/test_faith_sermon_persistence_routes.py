from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.routes.faith import router
from api.services.sermon_persistence import (
    SermonNotFoundError,
)


@pytest.fixture
def app():
    test_app = FastAPI()

    test_app.include_router(
        router,
        prefix="/api/v1/faith",
    )

    db = MagicMock()

    test_app.dependency_overrides[
        get_db
    ] = lambda: db

    test_app.dependency_overrides[
        get_current_user
    ] = lambda: SimpleNamespace(
        id=123,
        role="pastor",
    )

    yield test_app

    test_app.dependency_overrides.clear()


@pytest.fixture
def client(app):
    return TestClient(app)


def test_save_route_uses_authenticated_user(
    client,
    monkeypatch,
):
    captured = {}

    def fake_save_sermon_for_user(
        *,
        db,
        user_id,
        payload,
    ):
        captured["db"] = db
        captured["user_id"] = user_id
        captured["payload"] = payload

        return SimpleNamespace(
            id=77,
        )

    monkeypatch.setattr(
        "api.routes.faith.save_sermon_for_user",
        fake_save_sermon_for_user,
    )

    payload = {
        "title": "Faith Comes by Hearing",
        "scripture": "Romans 10:17",
        "author_id": 999,
    }

    response = client.post(
        "/api/v1/faith/sermon/save",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "Sermon saved",
        "sermon_id": 77,
    }

    assert captured["user_id"] == 123
    assert captured["payload"] == payload


def test_update_route_uses_authenticated_user(
    client,
    monkeypatch,
):
    captured = {}

    def fake_update_sermon_for_user(
        *,
        db,
        user_id,
        sermon_id,
        payload,
    ):
        captured["db"] = db
        captured["user_id"] = user_id
        captured["sermon_id"] = sermon_id
        captured["payload"] = payload

        return SimpleNamespace(
            id=sermon_id,
        )

    monkeypatch.setattr(
        "api.routes.faith.update_sermon_for_user",
        fake_update_sermon_for_user,
    )

    payload = {
        "title": "Updated Sermon",
        "scripture": "Romans 10:1-17",
    }

    response = client.put(
        "/api/v1/faith/sermon/update/42",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": "Sermon updated",
    }

    assert captured["user_id"] == 123
    assert captured["sermon_id"] == 42
    assert captured["payload"] == payload


def test_update_route_preserves_not_found(
    client,
    monkeypatch,
):
    def fake_update_sermon_for_user(
        **kwargs,
    ):
        raise SermonNotFoundError(
            "Sermon not found"
        )

    monkeypatch.setattr(
        "api.routes.faith.update_sermon_for_user",
        fake_update_sermon_for_user,
    )

    response = client.put(
        "/api/v1/faith/sermon/update/42",
        json={
            "title": "Attempted update",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Sermon not found",
    }


def test_save_route_rolls_back_on_failure(
    app,
    client,
    monkeypatch,
):
    db = app.dependency_overrides[
        get_db
    ]()

    app.dependency_overrides[
        get_db
    ] = lambda: db

    def fake_save_sermon_for_user(
        **kwargs,
    ):
        raise RuntimeError(
            "database failure"
        )

    monkeypatch.setattr(
        "api.routes.faith.save_sermon_for_user",
        fake_save_sermon_for_user,
    )

    response = client.post(
        "/api/v1/faith/sermon/save",
        json={
            "title": "Test",
        },
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Failed to save sermon",
    }

    db.rollback.assert_called_once()


def test_update_route_rolls_back_on_failure(
    app,
    client,
    monkeypatch,
):
    db = app.dependency_overrides[
        get_db
    ]()

    app.dependency_overrides[
        get_db
    ] = lambda: db

    def fake_update_sermon_for_user(
        **kwargs,
    ):
        raise RuntimeError(
            "database failure"
        )

    monkeypatch.setattr(
        "api.routes.faith.update_sermon_for_user",
        fake_update_sermon_for_user,
    )

    response = client.put(
        "/api/v1/faith/sermon/update/42",
        json={
            "title": "Test",
        },
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Failed to update sermon",
    }

    db.rollback.assert_called_once()
