from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import api.core.dependencies as dependencies
from api.services.xynassist_client import (
    XynAssistResponseError,
)
from main import app


CONVERSATION_ID = (
    "11111111-2222-3333-4444-555555555555"
)

CONVERSATION = {
    "id": CONVERSATION_ID,
    "product": "xynafaith",
    "title": "Sunday sermon",
    "status": "active",
    "created_at": "2026-08-31T03:00:00Z",
    "updated_at": "2026-08-31T03:00:00Z",
}

CONVERSATION_DETAIL = {
    **CONVERSATION,
    "messages": [],
}

TURN_RESPONSE = {
    "conversation": CONVERSATION_DETAIL,
    "user_message": {
        "id": "aaaaaaaa-2222-3333-4444-555555555555",
        "conversation_id": CONVERSATION_ID,
        "role": "user",
        "content": (
            "I need a Pentecostal sermon "
            "on Proverbs 3."
        ),
        "skill": "sermon.generate",
        "created_at": "2026-08-31T03:01:00Z",
    },
    "assistant_message": {
        "id": "bbbbbbbb-2222-3333-4444-555555555555",
        "conversation_id": CONVERSATION_ID,
        "role": "assistant",
        "content": (
            '{"title":"Trust the Lord"}'
        ),
        "skill": "sermon.generate",
        "created_at": "2026-08-31T03:01:01Z",
    },
    "skill": "sermon.generate",
}


class FakeUser:
    id = 123
    role = "member"


@pytest.fixture
def authorized_client():
    async def fake_current_user():
        return FakeUser()

    app.dependency_overrides[
        dependencies.get_current_user
    ] = fake_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


def test_create_conversation_uses_authenticated_user(
    monkeypatch,
    authorized_client,
):
    create_conversation = AsyncMock(
        return_value=CONVERSATION
    )

    class FakeXynAssistClient:
        async def create_conversation(
            self,
            *,
            external_user_id,
            title=None,
        ):
            return await create_conversation(
                external_user_id=external_user_id,
                title=title,
            )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations",
        json={
            "title": "Sunday sermon",
        },
    )

    assert response.status_code == 201
    assert response.json() == CONVERSATION

    create_conversation.assert_awaited_once_with(
        external_user_id="123",
        title="Sunday sermon",
    )


def test_create_conversation_allows_no_title(
    monkeypatch,
    authorized_client,
):
    create_conversation = AsyncMock(
        return_value={
            **CONVERSATION,
            "title": None,
        }
    )

    class FakeXynAssistClient:
        async def create_conversation(
            self,
            *,
            external_user_id,
            title=None,
        ):
            return await create_conversation(
                external_user_id=external_user_id,
                title=title,
            )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations",
        json={},
    )

    assert response.status_code == 201

    create_conversation.assert_awaited_once_with(
        external_user_id="123",
        title=None,
    )


def test_list_conversations_uses_authenticated_user(
    monkeypatch,
    authorized_client,
):
    list_conversations = AsyncMock(
        return_value=[CONVERSATION]
    )

    class FakeXynAssistClient:
        async def list_conversations(
            self,
            *,
            external_user_id,
        ):
            return await list_conversations(
                external_user_id=external_user_id,
            )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    response = authorized_client.get(
        "/api/v1/faith/conversations"
    )

    assert response.status_code == 200
    assert response.json() == [CONVERSATION]

    list_conversations.assert_awaited_once_with(
        external_user_id="123",
    )


def test_get_conversation_uses_authenticated_user(
    monkeypatch,
    authorized_client,
):
    get_conversation = AsyncMock(
        return_value=CONVERSATION_DETAIL
    )

    class FakeXynAssistClient:
        async def get_conversation(
            self,
            *,
            external_user_id,
            conversation_id,
        ):
            return await get_conversation(
                external_user_id=external_user_id,
                conversation_id=conversation_id,
            )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    response = authorized_client.get(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}"
    )

    assert response.status_code == 200
    assert response.json() == CONVERSATION_DETAIL

    get_conversation.assert_awaited_once_with(
        external_user_id="123",
        conversation_id=CONVERSATION_ID,
    )


def test_execute_turn_uses_authenticated_user(
    monkeypatch,
    authorized_client,
):
    execute_turn = AsyncMock(
        return_value=TURN_RESPONSE
    )

    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            *,
            external_user_id,
            conversation_id,
            content,
        ):
            return await execute_turn(
                external_user_id=external_user_id,
                conversation_id=conversation_id,
                content=content,
            )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    content = (
        "I need a Pentecostal sermon "
        "on Proverbs 3."
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": content,
        },
    )

    assert response.status_code == 200
    assert response.json() == TURN_RESPONSE

    execute_turn.assert_awaited_once_with(
        external_user_id="123",
        conversation_id=CONVERSATION_ID,
        content=content,
    )


def test_conversation_api_maps_xynassist_failure_to_503(
    monkeypatch,
    authorized_client,
):
    class FakeXynAssistClient:
        async def list_conversations(
            self,
            *,
            external_user_id,
        ):
            raise XynAssistResponseError(
                "XynAssist returned HTTP 503"
            )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    response = authorized_client.get(
        "/api/v1/faith/conversations"
    )

    assert response.status_code == 503

    assert response.json() == {
        "detail": (
            "Conversation service is "
            "temporarily unavailable"
        )
    }


def test_conversation_api_requires_authentication():
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/faith/conversations"
        )

    assert response.status_code == 401


def test_create_conversation_rejects_external_user_injection(
    authorized_client,
):
    response = authorized_client.post(
        "/api/v1/faith/conversations",
        json={
            "title": "Sunday sermon",
            "external_user_id": "999",
        },
    )

    assert response.status_code == 422


def test_create_conversation_rejects_product_injection(
    authorized_client,
):
    response = authorized_client.post(
        "/api/v1/faith/conversations",
        json={
            "title": "Sunday sermon",
            "product": "xynalegal",
        },
    )

    assert response.status_code == 422


def test_execute_turn_rejects_external_user_injection(
    authorized_client,
):
    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Make point two stronger.",
            "external_user_id": "999",
        },
    )

    assert response.status_code == 422


def test_execute_turn_rejects_product_injection(
    authorized_client,
):
    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Make point two stronger.",
            "product": "xynalegal",
        },
    )

    assert response.status_code == 422


def test_execute_turn_rejects_blank_content(
    authorized_client,
):
    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "   ",
        },
    )

    assert response.status_code == 422


def test_create_conversation_rejects_overlong_title(
    authorized_client,
):
    response = authorized_client.post(
        "/api/v1/faith/conversations",
        json={
            "title": "x" * 256,
        },
    )

    assert response.status_code == 422


def test_execute_turn_rejects_overlong_content(
    authorized_client,
):
    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "x" * 50_001,
        },
    )

    assert response.status_code == 422


def test_authenticated_user_identity_overrides_client_attempt(
    monkeypatch,
    authorized_client,
):
    create_conversation = AsyncMock(
        return_value=CONVERSATION
    )

    class FakeXynAssistClient:
        async def create_conversation(
            self,
            *,
            external_user_id,
            title=None,
        ):
            return await create_conversation(
                external_user_id=external_user_id,
                title=title,
            )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations",
        json={
            "title": "Sunday sermon",
        },
    )

    assert response.status_code == 201

    create_conversation.assert_awaited_once_with(
        external_user_id="123",
        title="Sunday sermon",
    )


def test_wrong_owner_upstream_not_found_is_not_exposed(
    monkeypatch,
    authorized_client,
):
    class FakeXynAssistClient:
        async def get_conversation(
            self,
            *,
            external_user_id,
            conversation_id,
        ):
            raise XynAssistResponseError(
                "XynAssist returned HTTP 404"
            )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    response = authorized_client.get(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}"
    )

    assert response.status_code == 503

    assert response.json() == {
        "detail": (
            "Conversation service is "
            "temporarily unavailable"
        )
    }
