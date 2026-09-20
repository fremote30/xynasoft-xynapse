from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.routes.faith_ministry as route
from api.core.dependencies import get_current_user
from api.db.database import get_db
from api.services.ministry_skill_service import (
    MinistryExecutionUncertainError,
)
from api.services.xynassist_client import (
    XynAssistResponseError,
)
from api.services.xyniva_usage_service import (
    XynivaUsageDenied,
)


@pytest.fixture
def app(monkeypatch):
    app = FastAPI()
    app.include_router(
        route.router,
        prefix="/api/v1/faith",
    )

    db = object()
    user = SimpleNamespace(
        id=77,
        role="pastor",
    )

    app.dependency_overrides[get_db] = (
        lambda: db
    )
    app.dependency_overrides[
        get_current_user
    ] = lambda: user

    monkeypatch.setattr(
        route,
        "XYNASSIST_ENABLED",
        True,
    )

    return app, db, user


def test_ministry_requires_authentication(
    monkeypatch,
):
    app = FastAPI()
    app.include_router(
        route.router,
        prefix="/api/v1/faith",
    )

    app.dependency_overrides[get_db] = (
        lambda: object()
    )

    monkeypatch.setattr(
        route,
        "XYNASSIST_ENABLED",
        True,
    )

    client = TestClient(app)

    response = client.post(
        "/api/v1/faith/ministry/execute",
        json={
            "request_id": str(uuid4()),
            "skill": "sermon.generate",
            "input": {
                "input": "Grace",
            },
        },
    )

    assert response.status_code in {
        401,
        403,
    }


def test_disabled_xynassist_fails_before_execution(
    app,
    monkeypatch,
):
    application, _, _ = app

    execute_calls = []

    async def fake_execute(*args, **kwargs):
        execute_calls.append(kwargs)
        return {"title": "Should not run"}

    monkeypatch.setattr(
        route,
        "XYNASSIST_ENABLED",
        False,
    )
    monkeypatch.setattr(
        route,
        "execute_ministry_for_user",
        fake_execute,
    )

    response = TestClient(application).post(
        "/api/v1/faith/ministry/execute",
        json={
            "request_id": str(uuid4()),
            "skill": "sermon.generate",
            "input": {
                "input": "Grace",
            },
        },
    )

    assert response.status_code == 503
    assert execute_calls == []


def test_ministry_uses_authenticated_user_and_request_id(
    app,
    monkeypatch,
):
    application, db, user = app
    request_id = uuid4()
    seen = {}

    async def fake_execute(
        actual_db,
        *,
        user,
        request_id,
        skill,
        payload,
    ):
        seen.update(
            {
                "db": actual_db,
                "user": user,
                "request_id": request_id,
                "skill": skill,
                "payload": payload,
            }
        )
        return {
            "title": "Grace",
            "scripture": "Ephesians 2:8",
        }

    monkeypatch.setattr(
        route,
        "execute_ministry_for_user",
        fake_execute,
    )

    response = TestClient(application).post(
        "/api/v1/faith/ministry/execute",
        json={
            "request_id": str(request_id),
            "skill": "sermon.generate",
            "input": {
                "input": "Grace",
                "scripture": "Ephesians 2:8",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()

    assert UUID(body["request_id"]) == request_id
    assert body["skill"] == "sermon.generate"
    assert body["result"]["title"] == "Grace"

    assert seen["db"] is db
    assert seen["user"] is user
    assert seen["request_id"] == str(request_id)
    assert seen["skill"] == "sermon.generate"


def test_browser_cannot_supply_trusted_commercial_fields(
    app,
):
    application, _, _ = app

    response = TestClient(application).post(
        "/api/v1/faith/ministry/execute",
        json={
            "request_id": str(uuid4()),
            "skill": "biblical.research",
            "input": {
                "topic": "grace",
            },
            "external_user_id": "999",
            "entitlement_key": "xyniva.chat",
            "metric": "cheap_metric",
            "units": 999,
        },
    )

    assert response.status_code == 422


def test_unknown_skill_is_rejected_by_schema(
    app,
):
    application, _, _ = app

    response = TestClient(application).post(
        "/api/v1/faith/ministry/execute",
        json={
            "request_id": str(uuid4()),
            "skill": "sermon.destroy",
            "input": {},
        },
    )

    assert response.status_code == 422


def test_usage_denial_becomes_403(
    app,
    monkeypatch,
):
    application, _, _ = app

    async def fake_execute(*args, **kwargs):
        raise XynivaUsageDenied(
            "Missing entitlement"
        )

    monkeypatch.setattr(
        route,
        "execute_ministry_for_user",
        fake_execute,
    )

    response = TestClient(application).post(
        "/api/v1/faith/ministry/execute",
        json={
            "request_id": str(uuid4()),
            "skill": "biblical.research",
            "input": {
                "scripture": "Romans 8",
            },
        },
    )

    assert response.status_code == 403


def test_uncertain_execution_becomes_503(
    app,
    monkeypatch,
):
    application, _, _ = app

    async def fake_execute(*args, **kwargs):
        raise MinistryExecutionUncertainError(
            "uncertain"
        )

    monkeypatch.setattr(
        route,
        "execute_ministry_for_user",
        fake_execute,
    )

    response = TestClient(application).post(
        "/api/v1/faith/ministry/execute",
        json={
            "request_id": str(uuid4()),
            "skill": "sermon.generate",
            "input": {
                "input": "Grace",
            },
        },
    )

    assert response.status_code == 503
    assert (
        "same request ID"
        in response.json()["detail"]
    )


def test_remote_failure_becomes_502(
    app,
    monkeypatch,
):
    application, _, _ = app

    async def fake_execute(*args, **kwargs):
        raise XynAssistResponseError(
            "bad response"
        )

    monkeypatch.setattr(
        route,
        "execute_ministry_for_user",
        fake_execute,
    )

    response = TestClient(application).post(
        "/api/v1/faith/ministry/execute",
        json={
            "request_id": str(uuid4()),
            "skill": "sermon.refine",
            "input": {
                "sermon": {
                    "title": "Grace",
                },
                "instruction": "Deepen",
            },
        },
    )

    assert response.status_code == 502
