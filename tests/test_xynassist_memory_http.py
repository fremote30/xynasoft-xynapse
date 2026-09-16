from __future__ import annotations

import os

os.environ[
    "XYNASSIST_DATABASE_URL"
] = "sqlite://"

os.environ[
    "XYNASSIST_SERVICE_TOKEN"
] = "test-service-token"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from xynassist_service.db.database import Base, get_db
from xynassist_service.main import app
from xynassist_service.models.memory import Memory


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={
            "check_same_thread": False,
        },
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    Session = sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
    )

    session = Session()

    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


def headers(user_id: str) -> dict[str, str]:
    return {
        "X-XynAssist-Service-Token":
            "test-service-token",
        "X-XynAssist-External-User-Id":
            user_id,
    }


def test_create_and_list_memory(client):
    response = client.post(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("memory-user-1"),
        json={
            "memory_type": "preference",
            "key": "response_style",
            "value": "concise",
        },
    )

    assert response.status_code == 200

    created = response.json()

    assert created["product"] == "xynafaith"
    assert created["memory_type"] == "preference"
    assert created["key"] == "response_style"
    assert created["value"] == "concise"
    assert created["source"] == "explicit_user"
    assert created["status"] == "active"

    response = client.get(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("memory-user-1"),
    )

    assert response.status_code == 200

    memories = response.json()

    assert len(memories) == 1
    assert memories[0]["id"] == created["id"]


def test_memory_list_is_owner_scoped(client):
    first = client.post(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("owner-1"),
        json={
            "memory_type": "user_fact",
            "key": "translation",
            "value": "NIV",
        },
    )

    assert first.status_code == 200

    second = client.get(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("owner-2"),
    )

    assert second.status_code == 200
    assert second.json() == []


def test_update_memory_is_owner_scoped(client):
    created = client.post(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("owner-1"),
        json={
            "memory_type": "preference",
            "key": "response_style",
            "value": "concise",
        },
    ).json()

    denied = client.patch(
        (
            "/api/v1/integrations/xynafaith/"
            f"memories/{created['id']}"
        ),
        headers=headers("owner-2"),
        json={
            "value": "detailed",
        },
    )

    assert denied.status_code == 404

    updated = client.patch(
        (
            "/api/v1/integrations/xynafaith/"
            f"memories/{created['id']}"
        ),
        headers=headers("owner-1"),
        json={
            "value": "detailed",
        },
    )

    assert updated.status_code == 200
    assert updated.json()["value"] == "detailed"


def test_forget_memory_deactivates_it(client, db):
    created = client.post(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("owner-1"),
        json={
            "memory_type": "ministry_context",
            "key": "denomination",
            "value": "Baptist",
        },
    ).json()

    response = client.delete(
        (
            "/api/v1/integrations/xynafaith/"
            f"memories/{created['id']}"
        ),
        headers=headers("owner-1"),
    )

    assert response.status_code == 204

    listing = client.get(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("owner-1"),
    )

    assert listing.status_code == 200
    assert listing.json() == []

    db.expire_all()

    stored = db.get(
        Memory,
        created["id"],
    )

    assert stored is not None
    assert stored.status == "inactive"


def test_other_user_cannot_forget_memory(client):
    created = client.post(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("owner-1"),
        json={
            "memory_type": "user_fact",
            "key": "preferred_translation",
            "value": "NIV",
        },
    ).json()

    response = client.delete(
        (
            "/api/v1/integrations/xynafaith/"
            f"memories/{created['id']}"
        ),
        headers=headers("owner-2"),
    )

    assert response.status_code == 404

    listing = client.get(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("owner-1"),
    )

    assert len(listing.json()) == 1


def test_memory_routes_require_service_auth(client):
    response = client.get(
        "/api/v1/integrations/xynafaith/memories",
        headers={
            "X-XynAssist-External-User-Id":
                "memory-user-1",
        },
    )

    assert response.status_code == 401


def test_memory_routes_require_external_user(client):
    response = client.get(
        "/api/v1/integrations/xynafaith/memories",
        headers={
            "X-XynAssist-Service-Token":
                "test-service-token",
        },
    )

    assert response.status_code == 400


def test_client_cannot_supply_memory_ownership(client):
    response = client.post(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("real-owner"),
        json={
            "memory_type": "preference",
            "key": "language",
            "value": "English",
            "external_user_id": "attacker-owner",
            "product": "xynalegal",
        },
    )

    assert response.status_code == 422


def test_sensitive_memory_type_is_rejected(client):
    response = client.post(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("memory-user-1"),
        json={
            "memory_type": "pastoral_care",
            "key": "confidential_note",
            "value": "Sensitive information",
        },
    )

    assert response.status_code == 422


def test_blank_memory_value_is_rejected(client):
    response = client.post(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("memory-user-1"),
        json={
            "memory_type": "preference",
            "key": "language",
            "value": "   ",
        },
    )

    assert response.status_code == 422


def test_post_upsert_preserves_memory_identity(client):
    first = client.post(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("upsert-user"),
        json={
            "memory_type": "preference",
            "key": "response_style",
            "value": "concise",
        },
    )

    assert first.status_code == 200

    first_memory = first.json()

    second = client.post(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("upsert-user"),
        json={
            "memory_type": "preference",
            "key": "response_style",
            "value": "detailed",
        },
    )

    assert second.status_code == 200

    second_memory = second.json()

    assert second_memory["id"] == first_memory["id"]
    assert second_memory["value"] == "detailed"

    listing = client.get(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("upsert-user"),
    )

    assert listing.status_code == 200
    assert len(listing.json()) == 1


def test_post_reactivates_forgotten_memory(client):
    created = client.post(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("reactivate-user"),
        json={
            "memory_type": "preference",
            "key": "response_style",
            "value": "concise",
        },
    )

    assert created.status_code == 200

    original = created.json()

    forgotten = client.delete(
        (
            "/api/v1/integrations/xynafaith/"
            f"memories/{original['id']}"
        ),
        headers=headers("reactivate-user"),
    )

    assert forgotten.status_code == 204

    restored = client.post(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("reactivate-user"),
        json={
            "memory_type": "preference",
            "key": "response_style",
            "value": "structured",
        },
    )

    assert restored.status_code == 200

    restored_memory = restored.json()

    assert restored_memory["id"] == original["id"]
    assert restored_memory["status"] == "active"
    assert restored_memory["value"] == "structured"


def test_patch_cannot_reactivate_forgotten_memory(client):
    created = client.post(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("inactive-user"),
        json={
            "memory_type": "user_fact",
            "key": "preferred_translation",
            "value": "NIV",
        },
    )

    assert created.status_code == 200

    memory_id = created.json()["id"]

    forgotten = client.delete(
        (
            "/api/v1/integrations/xynafaith/"
            f"memories/{memory_id}"
        ),
        headers=headers("inactive-user"),
    )

    assert forgotten.status_code == 204

    patched = client.patch(
        (
            "/api/v1/integrations/xynafaith/"
            f"memories/{memory_id}"
        ),
        headers=headers("inactive-user"),
        json={
            "value": "ESV",
        },
    )

    assert patched.status_code == 404

    listing = client.get(
        "/api/v1/integrations/xynafaith/memories",
        headers=headers("inactive-user"),
    )

    assert listing.status_code == 200
    assert listing.json() == []
