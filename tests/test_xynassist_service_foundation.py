from __future__ import annotations

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from xynassist_service.core.security import (
    require_external_user,
    require_service_auth,
)
from xynassist_service.main import app


def test_xynassist_health():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "xynassist",
    }


def test_xynassist_root():
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "service": "XynAssist",
        "status": "running",
    }


def _trusted_test_app() -> FastAPI:
    test_app = FastAPI()

    @test_app.get(
        "/trusted",
        dependencies=[
            Depends(require_service_auth),
        ],
    )
    def trusted() -> dict[str, bool]:
        return {"trusted": True}

    @test_app.get(
        "/user",
        dependencies=[
            Depends(require_service_auth),
        ],
    )
    def user(
        external_user_id: str = Depends(
            require_external_user
        ),
    ) -> dict[str, str]:
        return {
            "external_user_id":
                external_user_id,
        }

    return test_app


def test_trusted_endpoint_accepts_valid_token(
    monkeypatch,
):
    monkeypatch.setenv(
        "XYNASSIST_SERVICE_TOKEN",
        "test-service-token",
    )

    client = TestClient(_trusted_test_app())

    response = client.get(
        "/trusted",
        headers={
            "X-XynAssist-Service-Token":
                "test-service-token",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "trusted": True,
    }


def test_trusted_endpoint_rejects_missing_token(
    monkeypatch,
):
    monkeypatch.setenv(
        "XYNASSIST_SERVICE_TOKEN",
        "test-service-token",
    )

    client = TestClient(_trusted_test_app())

    response = client.get("/trusted")

    assert response.status_code == 401


def test_trusted_endpoint_rejects_wrong_token(
    monkeypatch,
):
    monkeypatch.setenv(
        "XYNASSIST_SERVICE_TOKEN",
        "test-service-token",
    )

    client = TestClient(_trusted_test_app())

    response = client.get(
        "/trusted",
        headers={
            "X-XynAssist-Service-Token":
                "wrong-token",
        },
    )

    assert response.status_code == 401


def test_external_user_is_normalized(
    monkeypatch,
):
    monkeypatch.setenv(
        "XYNASSIST_SERVICE_TOKEN",
        "test-service-token",
    )

    client = TestClient(_trusted_test_app())

    response = client.get(
        "/user",
        headers={
            "X-XynAssist-Service-Token":
                "test-service-token",
            "X-XynAssist-External-User-Id":
                " 123 ",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "external_user_id": "123",
    }


def test_external_user_is_required(
    monkeypatch,
):
    monkeypatch.setenv(
        "XYNASSIST_SERVICE_TOKEN",
        "test-service-token",
    )

    client = TestClient(_trusted_test_app())

    response = client.get(
        "/user",
        headers={
            "X-XynAssist-Service-Token":
                "test-service-token",
        },
    )

    assert response.status_code == 400
