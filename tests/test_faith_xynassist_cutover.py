from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import api.routes.faith as faith_routes
from api.services.xynassist_client import (
    XynAssistResponseError,
)
from main import app


VALID_SERMON = {
    "title": "Trust the Lord",
    "scripture": "Provider scripture",
    "introduction": "Opening",
    "main_points": [
        {
            "title": "Trust",
            "content": "Trust God completely.",
        }
    ],
    "application": "Walk by faith.",
    "conclusion": "Trust Him.",
}


REQUEST = {
    "input": "Trusting God",
    "scripture": "Proverbs 3:5-6",
    "denomination": "pentecostal",
    "audience": "general congregation",
    "context": "",
    "tone": "balanced",
    "duration": "30",
}


@pytest.fixture
def authorized_client(monkeypatch):
    class FakeUser:
        role = "member"

    async def fake_current_user():
        return FakeUser()

    dependency = None

    for route in app.routes:
        if route.path == "/api/v1/faith/sermon":
            for dependant in route.dependant.dependencies:
                call = dependant.call

                if getattr(
                    call,
                    "__name__",
                    "",
                ) == "get_current_user":
                    dependency = call
                    break

    if dependency is None:
        raise AssertionError(
            "get_current_user dependency not found"
        )

    app.dependency_overrides[dependency] = (
        fake_current_user
    )

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_disabled_flag_uses_legacy_generator(
    monkeypatch,
    authorized_client,
):
    monkeypatch.setattr(
        faith_routes,
        "XYNASSIST_ENABLED",
        False,
    )

    legacy = lambda payload: dict(VALID_SERMON)

    monkeypatch.setattr(
        faith_routes,
        "generate_ai_response",
        legacy,
    )

    class ForbiddenXynAssistClient:
        def __init__(self):
            raise AssertionError(
                "XynAssist must not be called"
            )

    monkeypatch.setattr(
        faith_routes,
        "XynAssistClient",
        ForbiddenXynAssistClient,
    )

    response = authorized_client.post(
        "/api/v1/faith/sermon",
        json=REQUEST,
    )

    assert response.status_code == 200

    payload = response.json()

    assert (
        payload["scripture"]
        == "Proverbs 3:5-6"
    )


def test_enabled_flag_uses_xynassist(
    monkeypatch,
    authorized_client,
):
    monkeypatch.setattr(
        faith_routes,
        "XYNASSIST_ENABLED",
        True,
    )

    def forbidden_legacy(payload):
        raise AssertionError(
            "Legacy generator must not be called"
        )

    monkeypatch.setattr(
        faith_routes,
        "generate_ai_response",
        forbidden_legacy,
    )

    generate_sermon = AsyncMock(
        return_value=dict(VALID_SERMON)
    )

    class FakeXynAssistClient:
        def __init__(self):
            pass

        async def generate_sermon(
            self,
            payload,
        ):
            return await generate_sermon(payload)

    monkeypatch.setattr(
        faith_routes,
        "XynAssistClient",
        FakeXynAssistClient,
    )

    response = authorized_client.post(
        "/api/v1/faith/sermon",
        json=REQUEST,
    )

    assert response.status_code == 200

    result = response.json()

    assert (
        result["scripture"]
        == "Proverbs 3:5-6"
    )

    generate_sermon.assert_awaited_once()

    forwarded = (
        generate_sermon.await_args.args[0]
    )

    assert forwarded == REQUEST


def test_enabled_flag_supports_scripture_only(
    monkeypatch,
    authorized_client,
):
    monkeypatch.setattr(
        faith_routes,
        "XYNASSIST_ENABLED",
        True,
    )

    received = None

    class FakeXynAssistClient:
        async def generate_sermon(
            self,
            payload,
        ):
            nonlocal received
            received = payload

            sermon = dict(VALID_SERMON)
            sermon["scripture"] = "Psalm 23"

            return sermon

    monkeypatch.setattr(
        faith_routes,
        "XynAssistClient",
        FakeXynAssistClient,
    )

    request = {
        **REQUEST,
        "input": "",
        "scripture": "Psalm 23",
    }

    response = authorized_client.post(
        "/api/v1/faith/sermon",
        json=request,
    )

    assert response.status_code == 200
    assert response.json()["scripture"] == "Psalm 23"

    assert received is not None
    assert received["input"] == ""
    assert received["scripture"] == "Psalm 23"


def test_enabled_flag_maps_xynassist_failure_to_503(
    monkeypatch,
    authorized_client,
):
    monkeypatch.setattr(
        faith_routes,
        "XYNASSIST_ENABLED",
        True,
    )

    class FailingXynAssistClient:
        async def generate_sermon(
            self,
            payload,
        ):
            raise XynAssistResponseError(
                "XynAssist returned HTTP 503"
            )

    monkeypatch.setattr(
        faith_routes,
        "XynAssistClient",
        FailingXynAssistClient,
    )

    response = authorized_client.post(
        "/api/v1/faith/sermon",
        json=REQUEST,
    )

    assert response.status_code == 503

    assert response.json() == {
        "detail": (
            "Sermon generation service "
            "is temporarily unavailable"
        )
    }
