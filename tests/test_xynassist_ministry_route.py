from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from xynassist_service.ai.contracts import (
    ModelRequest,
    ModelResponse,
)
from xynassist_service.ai.registry import (
    clear_model_providers,
    register_model_provider,
)


SERVICE_TOKEN = "test-service-token"
EXTERNAL_USER = "123"


class FakeProvider:
    name = "fake"

    def __init__(self, content: str):
        self.content = content
        self.requests: list[ModelRequest] = []

    def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        self.requests.append(request)

        return ModelResponse(
            content=self.content,
            provider=self.name,
            model="fake-ministry-v1",
            input_tokens=10,
            output_tokens=20,
        )


def sermon_json() -> str:
    return json.dumps(
        {
            "title": "Grace",
            "scripture": "Ephesians 2:8-9",
            "introduction": "Grace is God's gift.",
            "main_points": [
                {
                    "title": "Gift",
                    "content": "Grace is received.",
                }
            ],
            "application": "Live from grace.",
            "conclusion": "Trust God's grace.",
        }
    )


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv(
        "XYNASSIST_SERVICE_TOKEN",
        SERVICE_TOKEN,
    )
    monkeypatch.setenv(
        "XYNASSIST_MODEL_PROVIDER",
        "fake",
    )

    clear_model_providers()

    from xynassist_service.main import app

    with TestClient(app) as test_client:
        yield test_client

    clear_model_providers()


def trusted_headers() -> dict[str, str]:
    return {
        "X-XynAssist-Service-Token": SERVICE_TOKEN,
        "X-XynAssist-External-User-Id": EXTERNAL_USER,
    }


def test_ministry_route_requires_service_auth(client):
    response = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers={
            "X-XynAssist-External-User-Id": EXTERNAL_USER,
        },
        json={
            "skill": "sermon.generate",
            "input": {
                "input": "Grace",
            },
        },
    )

    assert response.status_code == 401


def test_ministry_route_requires_external_user(client):
    response = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers={
            "X-XynAssist-Service-Token": SERVICE_TOKEN,
        },
        json={
            "skill": "sermon.generate",
            "input": {
                "input": "Grace",
            },
        },
    )

    assert response.status_code == 400


def test_ministry_route_rejects_user_identity_in_body(client):
    response = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers=trusted_headers(),
        json={
            "skill": "sermon.generate",
            "input": {
                "input": "Grace",
            },
            "external_user_id": "attacker-controlled",
        },
    )

    assert response.status_code == 422


def test_ministry_route_rejects_unknown_skill(client):
    response = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers=trusted_headers(),
        json={
            "skill": "unknown.skill",
            "input": {
                "input": "Grace",
            },
        },
    )

    assert response.status_code == 422


def test_ministry_route_executes_sermon_skill(client):
    provider = FakeProvider(
        sermon_json()
    )
    register_model_provider(provider)

    response = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers=trusted_headers(),
        json={
            "skill": "sermon.generate",
            "input": {
                "input": "Grace",
                "scripture": "Ephesians 2:8-9",
            },
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["skill"] == "sermon.generate"
    assert body["result"]["title"] == "Grace"
    assert (
        body["result"]["scripture"]
        == "Ephesians 2:8-9"
    )

    assert len(provider.requests) == 1


def test_ministry_route_rejects_invalid_skill_input(client):
    provider = FakeProvider(
        sermon_json()
    )
    register_model_provider(provider)

    response = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers=trusted_headers(),
        json={
            "skill": "sermon.generate",
            "input": {},
        },
    )

    assert response.status_code == 422
    assert provider.requests == []


def test_ministry_route_fails_closed_on_bad_model_output(client):
    provider = FakeProvider(
        "not-json"
    )
    register_model_provider(provider)

    response = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers=trusted_headers(),
        json={
            "skill": "sermon.generate",
            "input": {
                "input": "Grace",
            },
        },
    )

    assert response.status_code == 502
