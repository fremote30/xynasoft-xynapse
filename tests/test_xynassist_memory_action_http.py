from __future__ import annotations

import os
import uuid

os.environ[
    "XYNASSIST_DATABASE_URL"
] = "sqlite://"

os.environ[
    "XYNASSIST_SERVICE_TOKEN"
] = "test-service-token"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from xynassist_service.db.database import Base, get_db
from xynassist_service.main import app
from xynassist_service.models.action_execution import (
    ActionExecution,
)
from xynassist_service.models.memory import Memory
from xynassist_service.services.memories import (
    create_or_update_memory,
)


ENDPOINT = (
    "/api/v1/integrations/"
    "xynafaith/memory-actions/execute"
)


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


def headers(
    user_id: str,
    *,
    confirmed: bool | None = None,
) -> dict[str, str]:
    result = {
        "X-XynAssist-Service-Token":
            "test-service-token",
        "X-XynAssist-External-User-Id":
            user_id,
    }

    if confirmed is not None:
        result[
            "X-XynAssist-Action-Confirmed"
        ] = (
            "true"
            if confirmed
            else "false"
        )

    return result


def request_id() -> str:
    return str(uuid.uuid4())


def test_remember_executes_through_trusted_route(
    client,
    db,
):
    action_request_id = request_id()

    response = client.post(
        ENDPOINT,
        headers=headers("http-memory-user-1"),
        json={
            "request_id": action_request_id,
            "action_name": "memory.remember",
            "arguments": {
                "memory_type": "preference",
                "key": "response_style",
                "value": "concise",
            },
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["memory_type"] == "preference"
    assert payload["key"] == "response_style"
    assert payload["status"] == "active"

    db.expire_all()

    memories = db.execute(
        select(Memory).where(
            Memory.external_user_id
            == "http-memory-user-1"
        )
    ).scalars().all()

    executions = db.execute(
        select(ActionExecution).where(
            ActionExecution.external_user_id
            == "http-memory-user-1"
        )
    ).scalars().all()

    assert len(memories) == 1
    assert len(executions) == 1
    assert executions[0].request_id == (
        action_request_id
    )


def test_remember_exact_retry_replays(
    client,
    db,
):
    action_request_id = request_id()

    body = {
        "request_id": action_request_id,
        "action_name": "memory.remember",
        "arguments": {
            "memory_type": "user_fact",
            "key": "preferred_translation",
            "value": "NIV",
        },
    }

    first = client.post(
        ENDPOINT,
        headers=headers("retry-user"),
        json=body,
    )

    second = client.post(
        ENDPOINT,
        headers=headers("retry-user"),
        json=body,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()

    db.expire_all()

    memories = db.execute(
        select(Memory).where(
            Memory.external_user_id
            == "retry-user"
        )
    ).scalars().all()

    executions = db.execute(
        select(ActionExecution).where(
            ActionExecution.external_user_id
            == "retry-user"
        )
    ).scalars().all()

    assert len(memories) == 1
    assert len(executions) == 1


def test_conflicting_request_id_returns_409(
    client,
):
    action_request_id = request_id()

    first = client.post(
        ENDPOINT,
        headers=headers("conflict-user"),
        json={
            "request_id": action_request_id,
            "action_name": "memory.remember",
            "arguments": {
                "memory_type": "preference",
                "key": "response_style",
                "value": "concise",
            },
        },
    )

    assert first.status_code == 200

    conflict = client.post(
        ENDPOINT,
        headers=headers("conflict-user"),
        json={
            "request_id": action_request_id,
            "action_name": "memory.remember",
            "arguments": {
                "memory_type": "preference",
                "key": "response_style",
                "value": "detailed",
            },
        },
    )

    assert conflict.status_code == 409


def test_forget_requires_trusted_confirmation(
    client,
    db,
):
    memory = create_or_update_memory(
        db,
        external_user_id="forget-user",
        memory_type="ministry_context",
        key="denomination",
        value="Baptist",
    )
    memory_id = memory.id
    db.commit()

    action_request_id = request_id()

    response = client.post(
        ENDPOINT,
        headers=headers("forget-user"),
        json={
            "request_id": action_request_id,
            "action_name": "memory.forget",
            "arguments": {
                "memory_type": "ministry_context",
                "key": "denomination",
            },
        },
    )

    assert response.status_code == 409

    db.expire_all()

    stored = db.get(Memory, memory_id)

    assert stored is not None
    assert stored.status == "active"

    execution = db.execute(
        select(ActionExecution).where(
            ActionExecution.request_id
            == action_request_id
        )
    ).scalar_one_or_none()

    assert execution is None


def test_confirmed_forget_deactivates_memory(
    client,
    db,
):
    memory = create_or_update_memory(
        db,
        external_user_id="confirmed-user",
        memory_type="preference",
        key="response_style",
        value="concise",
    )
    memory_id = memory.id
    db.commit()

    response = client.post(
        ENDPOINT,
        headers=headers(
            "confirmed-user",
            confirmed=True,
        ),
        json={
            "request_id": request_id(),
            "action_name": "memory.forget",
            "arguments": {
                "memory_type": "preference",
                "key": "response_style",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"

    db.expire_all()

    stored = db.get(Memory, memory_id)

    assert stored is not None
    assert stored.status == "inactive"


def test_confirmed_forget_exact_retry_replays(
    client,
    db,
):
    create_or_update_memory(
        db,
        external_user_id="forget-retry-user",
        memory_type="user_fact",
        key="preferred_translation",
        value="NIV",
    )
    db.commit()

    action_request_id = request_id()

    body = {
        "request_id": action_request_id,
        "action_name": "memory.forget",
        "arguments": {
            "memory_type": "user_fact",
            "key": "preferred_translation",
        },
    }

    first = client.post(
        ENDPOINT,
        headers=headers(
            "forget-retry-user",
            confirmed=True,
        ),
        json=body,
    )

    assert first.status_code == 200

    second = client.post(
        ENDPOINT,
        headers=headers(
            "forget-retry-user",
            confirmed=False,
        ),
        json=body,
    )

    assert second.status_code == 200
    assert second.json() == first.json()

    db.expire_all()

    executions = db.execute(
        select(ActionExecution).where(
            ActionExecution.request_id
            == action_request_id
        )
    ).scalars().all()

    assert len(executions) == 1


def test_action_is_owner_scoped(
    client,
    db,
):
    memory = create_or_update_memory(
        db,
        external_user_id="real-owner",
        memory_type="preference",
        key="response_style",
        value="concise",
    )
    memory_id = memory.id
    db.commit()

    response = client.post(
        ENDPOINT,
        headers=headers(
            "other-owner",
            confirmed=True,
        ),
        json={
            "request_id": request_id(),
            "action_name": "memory.forget",
            "arguments": {
                "memory_type": "preference",
                "key": "response_style",
            },
        },
    )

    assert response.status_code == 404

    db.expire_all()

    stored = db.get(Memory, memory_id)

    assert stored is not None
    assert stored.status == "active"


def test_body_cannot_supply_external_identity(
    client,
):
    response = client.post(
        ENDPOINT,
        headers=headers("trusted-owner"),
        json={
            "request_id": request_id(),
            "action_name": "memory.remember",
            "external_user_id": "attacker-owner",
            "arguments": {
                "memory_type": "preference",
                "key": "response_style",
                "value": "concise",
            },
        },
    )

    assert response.status_code == 422


def test_confirmation_cannot_be_smuggled_in_arguments(
    client,
    db,
):
    memory = create_or_update_memory(
        db,
        external_user_id="smuggle-user",
        memory_type="preference",
        key="response_style",
        value="concise",
    )
    memory_id = memory.id
    db.commit()

    response = client.post(
        ENDPOINT,
        headers=headers("smuggle-user"),
        json={
            "request_id": request_id(),
            "action_name": "memory.forget",
            "arguments": {
                "memory_type": "preference",
                "key": "response_style",
                "confirmed": True,
            },
        },
    )

    assert response.status_code == 422

    db.expire_all()

    stored = db.get(Memory, memory_id)

    assert stored is not None
    assert stored.status == "active"


def test_route_requires_service_auth(
    client,
):
    response = client.post(
        ENDPOINT,
        headers={
            "X-XynAssist-External-User-Id":
                "unauthorized-user",
        },
        json={
            "request_id": request_id(),
            "action_name": "memory.remember",
            "arguments": {
                "memory_type": "preference",
                "key": "response_style",
                "value": "concise",
            },
        },
    )

    assert response.status_code == 401


def test_route_requires_external_user(
    client,
):
    response = client.post(
        ENDPOINT,
        headers={
            "X-XynAssist-Service-Token":
                "test-service-token",
        },
        json={
            "request_id": request_id(),
            "action_name": "memory.remember",
            "arguments": {
                "memory_type": "preference",
                "key": "response_style",
                "value": "concise",
            },
        },
    )

    assert response.status_code == 400


def test_invalid_confirmation_header_rejected(
    client,
):
    action_headers = headers("header-user")
    action_headers[
        "X-XynAssist-Action-Confirmed"
    ] = "yes"

    response = client.post(
        ENDPOINT,
        headers=action_headers,
        json={
            "request_id": request_id(),
            "action_name": "memory.remember",
            "arguments": {
                "memory_type": "preference",
                "key": "response_style",
                "value": "concise",
            },
        },
    )

    assert response.status_code == 400
