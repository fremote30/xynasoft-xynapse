from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from xynassist_service.ai.contracts import (
    ModelRequest,
    ModelResponse,
)
from xynassist_service.ai.registry import (
    clear_model_providers,
    register_model_provider,
)
from xynassist_service.db.database import Base, get_db
from xynassist_service.models.ai_execution import (
    AIExecution,
)
import xynassist_service.models  # noqa: F401


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

    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
    )

    Base.metadata.create_all(bind=engine)

    from xynassist_service.main import app

    def override_get_db():
        db = TestingSessionLocal()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            test_client.testing_session_local = (
                TestingSessionLocal
            )
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
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
            "request_id": "88888888-8888-4888-8888-888888888888",
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
            "request_id": "88888888-8888-4888-8888-888888888888",
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
            "request_id": "88888888-8888-4888-8888-888888888888",
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
            "request_id": "88888888-8888-4888-8888-888888888888",
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
            "request_id": "88888888-8888-4888-8888-888888888888",
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




def test_ministry_route_records_ai_execution(client):
    provider = FakeProvider(sermon_json())
    register_model_provider(provider)

    request_id = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"

    response = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers=trusted_headers(),
        json={
            "request_id": request_id,
            "skill": "sermon.generate",
            "input": {
                "input": "Grace",
            },
        },
    )

    assert response.status_code == 200

    db = client.testing_session_local()

    try:
        rows = db.query(AIExecution).all()
    finally:
        db.close()

    assert len(rows) == 1

    execution = rows[0]

    assert execution.product == "xynafaith"
    assert execution.external_user_id == EXTERNAL_USER
    assert execution.request_id == request_id
    assert execution.operation == "sermon.generate"
    assert execution.provider == "fake"
    assert execution.model == "fake-ministry-v1"
    assert execution.input_tokens == 10
    assert execution.output_tokens == 20
    assert execution.attempt_number == 1


def test_ministry_route_rejects_invalid_skill_input(client):
    provider = FakeProvider(
        sermon_json()
    )
    register_model_provider(provider)

    response = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers=trusted_headers(),
        json={
            "request_id": "88888888-8888-4888-8888-888888888888",
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
            "request_id": "88888888-8888-4888-8888-888888888888",
            "skill": "sermon.generate",
            "input": {
                "input": "Grace",
            },
        },
    )

    assert response.status_code == 502


def test_ministry_route_replays_completed_request(
    client,
):
    provider = FakeProvider(sermon_json())
    register_model_provider(provider)

    request = {
        "request_id": "99999999-9999-4999-8999-999999999999",
        "skill": "sermon.generate",
        "input": {
            "input": "Grace",
            "scripture": "Ephesians 2:8-9",
        },
    }

    first = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers=trusted_headers(),
        json=request,
    )

    second = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers=trusted_headers(),
        json=request,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()
    assert len(provider.requests) == 1

    db = client.testing_session_local()

    try:
        executions = db.query(AIExecution).all()
    finally:
        db.close()

    assert len(executions) == 1
    assert executions[0].request_id == request["request_id"]


def test_ministry_route_rejects_request_id_reuse_with_changed_input(
    client,
):
    provider = FakeProvider(sermon_json())
    register_model_provider(provider)

    request_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    first = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers=trusted_headers(),
        json={
            "request_id": request_id,
            "skill": "sermon.generate",
            "input": {
                "input": "Grace",
            },
        },
    )

    second = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers=trusted_headers(),
        json={
            "request_id": request_id,
            "skill": "sermon.generate",
            "input": {
                "input": "Faith",
            },
        },
    )

    assert first.status_code == 200
    assert second.status_code == 409
    assert second.json()["detail"] == (
        "request_id was already used "
        "for different ministry input"
    )
    assert len(provider.requests) == 1


class FailingProvider:
    name = "fake"

    def __init__(self):
        self.requests: list[ModelRequest] = []

    def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        self.requests.append(request)
        raise RuntimeError("simulated provider failure")


def test_ministry_route_failed_request_cannot_reexecute(
    client,
):
    provider = FailingProvider()
    register_model_provider(provider)

    request = {
        "request_id": "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
        "skill": "sermon.generate",
        "input": {
            "input": "Grace",
        },
    }

    with pytest.raises(
        RuntimeError,
        match="simulated provider failure",
    ):
        client.post(
            "/api/v1/integrations/xynafaith/ministry/execute",
            headers=trusted_headers(),
            json=request,
        )

    assert len(provider.requests) == 1

    second = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers=trusted_headers(),
        json=request,
    )

    assert second.status_code == 409
    assert second.json()["detail"] == (
        "Ministry request cannot be replayed"
    )
    assert len(provider.requests) == 1


def test_ministry_route_bad_output_failure_cannot_reexecute(
    client,
):
    provider = FakeProvider("not-json")
    register_model_provider(provider)

    request = {
        "request_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "skill": "sermon.generate",
        "input": {
            "input": "Grace",
        },
    }

    first = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers=trusted_headers(),
        json=request,
    )

    assert first.status_code == 502
    assert len(provider.requests) == 1

    db = client.testing_session_local()

    try:
        executions = db.query(AIExecution).all()
    finally:
        db.close()

    assert len(executions) == 1
    assert executions[0].request_id == request["request_id"]
    assert executions[0].operation == "sermon.generate"
    assert executions[0].provider == "fake"
    assert executions[0].model == "fake-ministry-v1"
    assert executions[0].input_tokens == 10
    assert executions[0].output_tokens == 20

    second = client.post(
        "/api/v1/integrations/xynafaith/ministry/execute",
        headers=trusted_headers(),
        json=request,
    )

    assert second.status_code == 409
    assert second.json()["detail"] == (
        "Ministry request cannot be replayed"
    )
    assert len(provider.requests) == 1

    db = client.testing_session_local()

    try:
        executions = db.query(AIExecution).all()
    finally:
        db.close()

    assert len(executions) == 1
