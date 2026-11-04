from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.routes.faith_ministry as route
from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.services.ministry_skill_service import MinistryExecutionError
from api.services.xynassist_client import XynAssistResponseError


@pytest.fixture
def app(monkeypatch):
    application = FastAPI()
    application.include_router(
        route.router,
        prefix="/api/v1/faith",
    )

    from types import SimpleNamespace

    user = SimpleNamespace(id=77, role="pastor")
    db = object()

    application.dependency_overrides[get_current_user] = lambda: user
    application.dependency_overrides[get_db] = lambda: db

    monkeypatch.setattr(route, "XYNASSIST_ENABLED", True)

    return application, user, db


def test_recovery_uses_authenticated_identity(app, monkeypatch):
    application, user, db = app
    request_id = str(uuid4())
    calls = []

    async def fake_reconcile(actual_db, *, user, request_id):
        calls.append((actual_db, user, request_id))
        return {
            "request_id": request_id,
            "skill": "sermon.generate",
            "status": "completed",
            "result": {"title": "Grace"},
        }

    monkeypatch.setattr(
        route, "reconcile_ministry_for_user", fake_reconcile
    )

    response = TestClient(application).get(
        f"/api/v1/faith/ministry/executions/{request_id}"
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert calls == [(db, user, request_id)]


def test_recovery_rejects_invalid_request_id(app):
    application, _, _ = app

    response = TestClient(application).get(
        "/api/v1/faith/ministry/executions/not-a-uuid"
    )

    assert response.status_code == 422


def test_recovery_fails_closed_when_disabled(app, monkeypatch):
    application, _, _ = app
    monkeypatch.setattr(route, "XYNASSIST_ENABLED", False)

    response = TestClient(application).get(
        f"/api/v1/faith/ministry/executions/{uuid4()}"
    )

    assert response.status_code == 503


def test_recovery_does_not_expose_other_users(app, monkeypatch):
    application, _, _ = app

    async def fake_reconcile(*args, **kwargs):
        raise MinistryExecutionError("Not owned by user")

    monkeypatch.setattr(
        route, "reconcile_ministry_for_user", fake_reconcile
    )

    response = TestClient(application).get(
        f"/api/v1/faith/ministry/executions/{uuid4()}"
    )

    assert response.status_code == 404


def test_remote_failure_does_not_claim_completion(app, monkeypatch):
    application, _, _ = app

    async def fake_reconcile(*args, **kwargs):
        raise XynAssistResponseError("Remote status unavailable")

    monkeypatch.setattr(
        route, "reconcile_ministry_for_user", fake_reconcile
    )

    response = TestClient(application).get(
        f"/api/v1/faith/ministry/executions/{uuid4()}"
    )

    assert response.status_code == 502
