from __future__ import annotations

from unittest.mock import AsyncMock, Mock

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


REQUEST_ID = (
    "66666666-7777-4888-8999-aaaaaaaaaaaa"
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
def authorized_client(monkeypatch):
    async def fake_current_user():
        return FakeUser()

    app.dependency_overrides[
        dependencies.get_current_user
    ] = fake_current_user

    # Route tests do not depend on the pending-action
    # database table unless a test explicitly opts into
    # pending-state behavior. Keep that service boundary
    # isolated from the real database by default.
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_sermon_delete",
        Mock(return_value=None),
    )

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
            context=None,
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
            "request_id": REQUEST_ID,
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


def test_execute_turn_requires_request_id(
    authorized_client,
):
    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Make point two stronger.",
        },
    )

    assert response.status_code == 422


def test_execute_turn_rejects_invalid_request_id(
    authorized_client,
):
    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Make point two stronger.",
            "request_id": "not-a-uuid",
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
            "request_id": REQUEST_ID,
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
            "request_id": REQUEST_ID,
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
            "request_id": REQUEST_ID,
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
            "request_id": REQUEST_ID,
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



def test_execute_turn_accepts_sermon_action_context(
    monkeypatch,
    authorized_client,
):
    # This test is specifically about the transport
    # boundary. Return a normal AI response so the trusted
    # action executor is not part of this assertion.
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
            context=None,
        ):
            return await execute_turn(
                external_user_id=external_user_id,
                conversation_id=conversation_id,
                content=content,
                context=context,
            )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": (
                "Make the conclusion stronger."
            ),
            "request_id": REQUEST_ID,
            "sermon": {
                "data": {
                    "title": "Trust the Lord",
                    "scripture": (
                        "Proverbs 3:5-6"
                    ),
                    "introduction": (
                        "Trust begins where sight ends."
                    ),
                    "points": [],
                    "conclusion": (
                        "Trust the Lord completely."
                    ),
                },
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == TURN_RESPONSE

    # The sermon body remains inside XynaFaith.
    # XynAssist receives only the minimal trusted resource
    # signal needed to resolve the conversational referent.
    execute_turn.assert_awaited_once_with(
        external_user_id="123",
        conversation_id=CONVERSATION_ID,
        content=(
            "Make the conclusion stronger."
        ),
        context={
            "active_resource": "sermon",
            "resource_persisted": False,
        },
    )


def test_execute_turn_marks_saved_sermon_as_persisted(
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
            context=None,
        ):
            return await execute_turn(
                external_user_id=external_user_id,
                conversation_id=conversation_id,
                content=content,
                context=context,
            )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Save these changes.",
            "request_id": REQUEST_ID,
            "sermon": {
                "id": 42,
                "data": {
                    "title": "Trust the Lord",
                    "scripture": "Proverbs 3:5-6",
                    "points": [],
                },
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == TURN_RESPONSE

    execute_turn.assert_awaited_once_with(
        external_user_id="123",
        conversation_id=CONVERSATION_ID,
        content="Save these changes.",
        context={
            "active_resource": "sermon",
            "resource_persisted": True,
        },
    )

def test_execute_turn_rejects_identity_inside_sermon_context(
    authorized_client,
):
    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Save this.",
            "request_id": REQUEST_ID,
            "sermon": {
                "data": {
                    "title": "Trust the Lord",
                },
                "external_user_id": "999",
            },
        },
    )

    assert response.status_code == 422


def test_execute_turn_rejects_invalid_sermon_id(
    authorized_client,
):
    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Save this.",
            "request_id": REQUEST_ID,
            "sermon": {
                "id": 0,
                "data": {
                    "title": "Trust the Lord",
                },
            },
        },
    )

    assert response.status_code == 422


def test_execute_turn_executes_sermon_save_as_authenticated_user(
    monkeypatch,
    authorized_client,
):
    action_response = {
        "conversation_id": CONVERSATION_ID,
        "user_message_id": (
            "aaaaaaaa-2222-3333-4444-555555555555"
        ),
        "action": {
            "name": "sermon.save",
            "arguments": {},
        },
    }

    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            *,
            external_user_id,
            conversation_id,
            content,
            context=None,
        ):
            assert external_user_id == "123"
            assert conversation_id == CONVERSATION_ID
            assert content == "Save this."

            return action_response

    execute_action = Mock(
        return_value={
            "name": "sermon.save",
            "status": "completed",
            "result": {
                "sermon_id": 42,
            },
        }
    )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "execute_conversation_action",
        execute_action,
    )

    sermon_data = {
        "title": "Trust the Lord",
        "scripture": "Proverbs 3:5-6",
        "points": [],
    }

    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Save this.",
            "request_id": REQUEST_ID,
            "sermon": {
                "data": sermon_data,
            },
        },
    )

    assert response.status_code == 200

    execute_action.assert_called_once()

    call = execute_action.call_args.kwargs

    assert call["user_id"] == 123
    assert call["request_id"] == REQUEST_ID
    assert call["source_message_id"] == (
        "aaaaaaaa-2222-3333-4444-555555555555"
    )
    assert call["action"] == {
        "name": "sermon.save",
        "arguments": {},
    }
    assert call["sermon_id"] is None
    assert call["sermon_data"] == sermon_data

    payload = response.json()

    assert payload["action"] == {
        "name": "sermon.save",
        "status": "completed",
        "result": {
            "sermon_id": 42,
        },
    }


def test_execute_turn_leaves_ai_response_unchanged(
    monkeypatch,
    authorized_client,
):
    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            return TURN_RESPONSE

    execute_action = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "execute_conversation_action",
        execute_action,
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": (
                "Make point two more pastoral."
            ),
            "request_id": REQUEST_ID,
        },
    )

    assert response.status_code == 200
    assert response.json() == TURN_RESPONSE

    execute_action.assert_not_called()


def test_execute_turn_action_requires_sermon_context(
    monkeypatch,
    authorized_client,
):
    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            return {
                "conversation_id": CONVERSATION_ID,
                "user_message_id": (
                    "aaaaaaaa-2222-3333-4444-555555555555"
                ),
                "action": {
                    "name": "sermon.save",
                    "arguments": {},
                },
            }

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Save this.",
            "request_id": REQUEST_ID,
        },
    )

    assert response.status_code == 422

    assert response.json() == {
        "detail": (
            "Current sermon context is required"
        )
    }


def test_execute_turn_rejects_unknown_action(
    monkeypatch,
    authorized_client,
):
    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            return {
                "conversation_id": CONVERSATION_ID,
                "user_message_id": (
                    "aaaaaaaa-2222-3333-4444-555555555555"
                ),
                "action": {
                    "name": "sermon.publish",
                    "arguments": {},
                },
            }

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Delete this.",
            "request_id": REQUEST_ID,
            "sermon": {
                "data": {
                    "title": "Sermon",
                },
            },
        },
    )

    assert response.status_code == 422

    assert response.json() == {
        "detail": (
            "Unsupported conversation action"
        )
    }


def test_execute_turn_records_pending_sermon_delete(
    monkeypatch,
    authorized_client,
):
    confirmation_response = {
        "conversation_id": CONVERSATION_ID,
        "user_message_id": (
            "aaaaaaaa-2222-3333-4444-555555555555"
        ),
        "action": {
            "name": "sermon.delete",
            "arguments": {},
        },
        "prompt": (
            "Are you sure you want to delete this sermon?"
        ),
    }

    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            return confirmation_response

    record_pending = Mock()
    execute_action = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "record_pending_sermon_delete",
        record_pending,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "execute_conversation_action",
        execute_action,
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Delete this sermon.",
            "request_id": REQUEST_ID,
            "sermon": {
                "id": 42,
                "data": {
                    "title": "Trust the Lord",
                },
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == confirmation_response

    record_pending.assert_called_once_with(
        db=record_pending.call_args.kwargs["db"],
        user_id=123,
        conversation_id=CONVERSATION_ID,
        sermon_id=42,
        source_message_id=(
            "aaaaaaaa-2222-3333-4444-555555555555"
        ),
    )

    execute_action.assert_not_called()


def test_execute_turn_delete_confirmation_requires_saved_sermon(
    monkeypatch,
    authorized_client,
):
    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            return {
                "conversation_id": CONVERSATION_ID,
                "user_message_id": (
                    "aaaaaaaa-2222-3333-4444-555555555555"
                ),
                "action": {
                    "name": "sermon.delete",
                    "arguments": {},
                },
                "prompt": (
                    "Are you sure you want to delete "
                    "this sermon?"
                ),
            }

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Delete this sermon.",
            "request_id": REQUEST_ID,
            "sermon": {
                "data": {
                    "title": "Unsaved sermon",
                },
            },
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "A saved sermon is required for deletion"
        )
    }


def test_execute_turn_rejects_unknown_confirmation_action(
    monkeypatch,
    authorized_client,
):
    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            return {
                "conversation_id": CONVERSATION_ID,
                "user_message_id": (
                    "aaaaaaaa-2222-3333-4444-555555555555"
                ),
                "action": {
                    "name": "sermon.update",
                    "arguments": {},
                },
                "prompt": "Confirm this action?",
            }

    execute_action = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "execute_conversation_action",
        execute_action,
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Do this.",
            "request_id": REQUEST_ID,
            "sermon": {
                "id": 42,
                "data": {
                    "title": "Sermon",
                },
            },
        },
    )

    assert response.status_code == 502
    execute_action.assert_not_called()


def test_execute_turn_forwards_trusted_pending_delete(
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
            context=None,
        ):
            return await execute_turn(
                external_user_id=external_user_id,
                conversation_id=conversation_id,
                content=content,
                context=context,
            )

    pending = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_sermon_delete",
        Mock(return_value=pending),
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Yes, delete it.",
            "request_id": REQUEST_ID,
            "sermon": {
                "id": 42,
                "data": {
                    "title": "Trust the Lord",
                },
            },
        },
    )

    assert response.status_code == 200

    execute_turn.assert_awaited_once_with(
        external_user_id="123",
        conversation_id=CONVERSATION_ID,
        content="Yes, delete it.",
        context={
            "active_resource": "sermon",
            "resource_persisted": True,
            "pending_action": "sermon.delete",
        },
    )


def test_execute_turn_withholds_pending_delete_for_other_sermon(
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
            context=None,
        ):
            return await execute_turn(
                external_user_id=external_user_id,
                conversation_id=conversation_id,
                content=content,
                context=context,
            )

    lookup = Mock(return_value=None)

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_sermon_delete",
        lookup,
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Yes.",
            "request_id": REQUEST_ID,
            "sermon": {
                "id": 84,
                "data": {
                    "title": "Different sermon",
                },
            },
        },
    )

    assert response.status_code == 200

    lookup.assert_called_once_with(
        db=lookup.call_args.kwargs["db"],
        user_id=123,
        conversation_id=CONVERSATION_ID,
        sermon_id=84,
    )

    execute_turn.assert_awaited_once_with(
        external_user_id="123",
        conversation_id=CONVERSATION_ID,
        content="Yes.",
        context={
            "active_resource": "sermon",
            "resource_persisted": True,
        },
    )
