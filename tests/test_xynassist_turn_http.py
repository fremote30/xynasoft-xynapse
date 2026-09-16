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
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session as OrmSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from xynassist_service.db.database import Base
from xynassist_service.db.database import get_db
from xynassist_service.main import app
from xynassist_service.models.conversation import (
    Conversation,
)
from xynassist_service.models.message import (
    ConversationMessage,
)


def _assign_sqlite_message_sequences(
    session,
    flush_context,
    instances,
):
    """Emulate PostgreSQL message sequencing in SQLite tests."""
    pending = [
        obj
        for obj in session.new
        if isinstance(obj, ConversationMessage)
        and obj.sequence_number is None
    ]

    if not pending:
        return

    current = session.execute(
        select(
            func.coalesce(
                func.max(
                    ConversationMessage.sequence_number
                ),
                0,
            )
        )
    ).scalar_one()

    for offset, message in enumerate(
        pending,
        start=1,
    ):
        message.sequence_number = current + offset


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

    event.listen(
        OrmSession,
        "before_flush",
        _assign_sqlite_message_sequences,
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

    app.dependency_overrides[get_db] = (
        override_db
    )

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


def create_conversation(
    db,
    *,
    user_id: str,
) -> Conversation:
    conversation = Conversation(
        id=str(uuid.uuid4()),
        product="xynafaith",
        external_user_id=user_id,
        title="HTTP turn test",
        status="active",
    )

    db.add(conversation)
    db.commit()

    return conversation


def test_turn_executes_and_persists(
    client,
    db,
    monkeypatch,
):
    user_id = "http-user-1"

    conversation = create_conversation(
        db,
        user_id=user_id,
    )

    from xynassist_service.services import turns
    from xynassist_service.services.turn_engine import (
        TurnEngineResult,
    )

    def fake_engine(
        *,
        content,
        context,
    ):
        assert content == "Hello Xyniva"
        assert context is None

        return TurnEngineResult(
            content="Hello from Xyniva.",
            skill="conversation.respond",
        )

    monkeypatch.setattr(
        turns,
        "execute_turn_engine",
        fake_engine,
    )

    request_id = str(uuid.uuid4())

    response = client.post(
        (
            "/api/v1/integrations/xynafaith/"
            f"conversations/{conversation.id}/turns"
        ),
        headers=headers(user_id),
        json={
            "request_id": request_id,
            "content": "Hello Xyniva",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["skill"] == (
        "conversation.respond"
    )

    assert (
        payload["user_message"]["content"]
        == "Hello Xyniva"
    )

    assert (
        payload["assistant_message"]["content"]
        == "Hello from Xyniva."
    )

    assert payload["user_message_id"] == (
        payload["user_message"]["id"]
    )

    assert len(
        payload["conversation"]["messages"]
    ) == 2


def test_identical_retry_executes_engine_once(
    client,
    db,
    monkeypatch,
):
    user_id = "http-user-2"

    conversation = create_conversation(
        db,
        user_id=user_id,
    )

    request_id = str(uuid.uuid4())

    url = (
        "/api/v1/integrations/xynafaith/"
        f"conversations/{conversation.id}/turns"
    )

    body = {
        "request_id": request_id,
        "content": "Retry me",
        "context": {
            "active_resource": "sermon",
        },
    }

    calls = []

    from xynassist_service.services import turns
    from xynassist_service.services.turn_engine import (
        TurnEngineResult,
    )

    def fake_engine(
        *,
        content,
        context,
    ):
        calls.append(
            {
                "content": content,
                "context": context,
            }
        )

        return TurnEngineResult(
            content="Executed exactly once",
            skill="conversation.respond",
        )

    monkeypatch.setattr(
        turns,
        "execute_turn_engine",
        fake_engine,
    )

    first = client.post(
        url,
        headers=headers(user_id),
        json=body,
    )

    second = client.post(
        url,
        headers=headers(user_id),
        json=body,
    )

    assert first.status_code == 200
    assert second.status_code == 200

    assert second.json() == first.json()

    assert calls == [
        {
            "content": "Retry me",
            "context": {
                "active_resource": "sermon",
            },
        }
    ]


def test_same_request_different_content_is_409(
    client,
    db,
    monkeypatch,
):
    user_id = "http-user-3"

    conversation = create_conversation(
        db,
        user_id=user_id,
    )

    from xynassist_service.services import turns
    from xynassist_service.services.turn_engine import (
        TurnEngineResult,
    )

    def fake_engine(
        *,
        content,
        context,
    ):
        return TurnEngineResult(
            content="Processed by Xyniva.",
            skill="conversation.respond",
        )

    monkeypatch.setattr(
        turns,
        "execute_turn_engine",
        fake_engine,
    )

    request_id = str(uuid.uuid4())

    url = (
        "/api/v1/integrations/xynafaith/"
        f"conversations/{conversation.id}/turns"
    )

    first = client.post(
        url,
        headers=headers(user_id),
        json={
            "request_id": request_id,
            "content": "First content",
        },
    )

    assert first.status_code == 200

    conflict = client.post(
        url,
        headers=headers(user_id),
        json={
            "request_id": request_id,
            "content": "Different content",
        },
    )

    assert conflict.status_code == 409


def test_foreign_conversation_is_404(
    client,
    db,
):
    conversation = create_conversation(
        db,
        user_id="owner-user",
    )

    response = client.post(
        (
            "/api/v1/integrations/xynafaith/"
            f"conversations/{conversation.id}/turns"
        ),
        headers=headers("foreign-user"),
        json={
            "request_id": str(uuid.uuid4()),
            "content": "Do not allow this",
        },
    )

    assert response.status_code == 404


def test_invalid_request_id_is_422(
    client,
    db,
):
    user_id = "http-user-5"

    conversation = create_conversation(
        db,
        user_id=user_id,
    )

    response = client.post(
        (
            "/api/v1/integrations/xynafaith/"
            f"conversations/{conversation.id}/turns"
        ),
        headers=headers(user_id),
        json={
            "request_id": "not-a-uuid",
            "content": "Hello",
        },
    )

    assert response.status_code == 422
