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


def test_saved_sermon_transform_uses_trusted_persisted_source(
    app,
    monkeypatch,
):
    application, db, user = app
    request_id = uuid4()
    seen = {}

    sermon = SimpleNamespace(
        id=42,
        author_id=user.id,
        title="Trust the Lord",
        scripture="Proverbs 3:5-6",
        content="legacy content",
        sermon_data={
            "title": "Trust the Lord",
            "introduction": "Trust begins here.",
            "application": "Walk by faith.",
        },
    )

    class FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return sermon

    class FakeDB:
        def query(self, *args, **kwargs):
            return FakeQuery()

    trusted_db = FakeDB()
    application.dependency_overrides[get_db] = (
        lambda: trusted_db
    )

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
            "source_title": payload["source_title"],
            "pieces": [
                {
                    "format": "whatsapp_summary",
                    "title": "Summary",
                    "content": "Trusted summary",
                }
            ],
        }

    monkeypatch.setattr(
        route,
        "execute_ministry_for_user",
        fake_execute,
    )

    response = TestClient(application).post(
        "/api/v1/faith/ministry/sermons/42/transform",
        json={
            "request_id": str(request_id),
            "formats": ["whatsapp_summary"],
            "audience": "church members",
            "tone": "warm",
            "denomination": "general",
            "context": "Sunday follow-up",
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert UUID(body["request_id"]) == request_id
    assert body["sermon_id"] == 42

    assert seen["db"] is trusted_db
    assert seen["user"] is user
    assert seen["request_id"] == str(request_id)
    assert seen["skill"] == "content.transform"

    assert seen["payload"]["source_title"] == "Trust the Lord"
    assert (
        seen["payload"]["source_scripture"]
        == "Proverbs 3:5-6"
    )

    source = __import__("json").loads(
        seen["payload"]["source_content"]
    )
    assert source == sermon.sermon_data
    assert seen["payload"]["audience"] == "church members"
    assert seen["payload"]["tone"] == "warm"


def test_saved_sermon_transform_fails_closed_when_not_owned(
    app,
    monkeypatch,
):
    application, _, _ = app
    execute_calls = []

    class FakeQuery:
        def filter(self, *args, **kwargs):
            return self

        def first(self):
            return None

    class FakeDB:
        def query(self, *args, **kwargs):
            return FakeQuery()

    application.dependency_overrides[get_db] = (
        lambda: FakeDB()
    )

    async def fake_execute(*args, **kwargs):
        execute_calls.append(kwargs)
        return {}

    monkeypatch.setattr(
        route,
        "execute_ministry_for_user",
        fake_execute,
    )

    response = TestClient(application).post(
        "/api/v1/faith/ministry/sermons/999/transform",
        json={
            "request_id": str(uuid4()),
            "formats": ["newsletter"],
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Sermon not found"
    assert execute_calls == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("source_title", "Attacker title"),
        ("source_scripture", "Attacker scripture"),
        ("source_content", "Attacker sermon"),
    ],
)
def test_saved_sermon_transform_rejects_client_source_fields(
    app,
    field,
    value,
):
    application, _, _ = app

    body = {
        "request_id": str(uuid4()),
        "formats": ["social_post"],
        field: value,
    }

    response = TestClient(application).post(
        "/api/v1/faith/ministry/sermons/42/transform",
        json=body,
    )

    assert response.status_code == 422


def test_saved_sermon_transform_rejects_duplicate_formats(
    app,
):
    application, _, _ = app

    response = TestClient(application).post(
        "/api/v1/faith/ministry/sermons/42/transform",
        json={
            "request_id": str(uuid4()),
            "formats": [
                "newsletter",
                "newsletter",
            ],
        },
    )

    assert response.status_code == 422


def test_saved_sermon_transform_rejects_empty_formats(
    app,
):
    application, _, _ = app

    response = TestClient(application).post(
        "/api/v1/faith/ministry/sermons/42/transform",
        json={
            "request_id": str(uuid4()),
            "formats": [],
        },
    )

    assert response.status_code == 422
