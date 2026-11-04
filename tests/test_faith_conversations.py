from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient

import api.core.dependencies as dependencies
from api.services.xynassist_client import (
    XynAssistResponseError,
)
from main import app



@pytest.fixture(autouse=True)
def bypass_xyniva_turn_metering(monkeypatch):
    """
    Existing conversation tests exercise the Faith/XynAssist
    transport and trusted-action contracts, not V2 quota
    accounting.

    Route-level metering behavior is covered separately by
    test_faith_conversation_metering.py.
    """
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "reserve_conversation_turn",
        Mock(),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "consume_conversation_turn",
        Mock(),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "release_conversation_turn",
        Mock(),
    )


@pytest.fixture(autouse=True)
def enable_xynassist_for_conversation_tests(
    monkeypatch,
):
    """
    Legacy conversation tests exercise the enabled XynAssist
    integration path. Production remains fail-closed by default.
    """
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XYNASSIST_ENABLED",
        True,
    )


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
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_memory_forget",
        Mock(return_value=None),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_service_assignment",
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
            request_id,
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
            request_id,
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
            request_id,
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
            request_id,
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
            request_id,
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
            request_id,
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


def test_execute_turn_records_pending_service_assignment(
    monkeypatch,
    authorized_client,
):
    response_payload = {
        "conversation_id": CONVERSATION_ID,
        "user_message_id": (
            "aaaaaaaa-2222-3333-4444-555555555555"
        ),
        "action": {
            "name": "service_assignment.create",
            "arguments": {
                "event_id": 10,
                "group_id": 20,
                "church_membership_id": 30,
                "service_role": "Usher",
            },
        },
        "prompt": "Assign this member as an usher?",
    }

    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            return response_payload

    validate_assignment = Mock()
    record_pending = Mock()
    execute_action = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "_trusted_church_intelligence_context",
        Mock(return_value={"church_id": 7}),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "validate_service_assignment_for_user",
        validate_assignment,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "record_pending_service_assignment",
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
            "content": "Assign this member as an usher.",
            "request_id": REQUEST_ID,
            "church_id": 7,
        },
    )

    assert response.status_code == 200
    assert response.json() == response_payload

    validate_assignment.assert_called_once_with(
        validate_assignment.call_args.args[0],
        user=validate_assignment.call_args.kwargs["user"],
        church_id=7,
        event_id=10,
        group_id=20,
        church_membership_id=30,
        service_role="Usher",
    )

    record_pending.assert_called_once()

    pending_kwargs = record_pending.call_args.kwargs

    assert pending_kwargs["user_id"] == 123
    assert pending_kwargs["conversation_id"] == CONVERSATION_ID
    assert pending_kwargs["church_id"] == 7
    assert pending_kwargs["arguments"] == {
        "event_id": 10,
        "group_id": 20,
        "church_membership_id": 30,
        "service_role": "Usher",
    }
    assert pending_kwargs["source_message_id"] == (
        "aaaaaaaa-2222-3333-4444-555555555555"
    )
    assert isinstance(
        pending_kwargs["action_request_id"],
        str,
    )
    assert pending_kwargs["action_request_id"]

    execute_action.assert_not_called()


def test_execute_turn_service_assignment_requires_church_context(
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
                    "name": "service_assignment.create",
                    "arguments": {
                        "event_id": 10,
                        "group_id": 20,
                        "church_membership_id": 30,
                        "service_role": "Usher",
                    },
                },
                "prompt": "Assign this member?",
            }

    validate_assignment = Mock()
    record_pending = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "validate_service_assignment_for_user",
        validate_assignment,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "record_pending_service_assignment",
        record_pending,
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Assign this member.",
            "request_id": REQUEST_ID,
        },
    )

    assert response.status_code == 502
    validate_assignment.assert_not_called()
    record_pending.assert_not_called()


def test_execute_turn_rejects_invalid_service_assignment_before_pending(
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
                    "name": "service_assignment.create",
                    "arguments": {
                        "event_id": 10,
                        "group_id": 20,
                        "church_membership_id": 30,
                        "service_role": "Usher",
                    },
                },
                "prompt": "Assign this member?",
            }

    from api.services.church_operations_service import (
        ChurchOperationsValidationError,
    )

    validate_assignment = Mock(
        side_effect=ChurchOperationsValidationError(
            "Church member is not an active member "
            "of this service team"
        )
    )
    record_pending = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "_trusted_church_intelligence_context",
        Mock(return_value={"church_id": 7}),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "validate_service_assignment_for_user",
        validate_assignment,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "record_pending_service_assignment",
        record_pending,
    )

    response = authorized_client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Assign this member.",
            "request_id": REQUEST_ID,
            "church_id": 7,
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "Church member is not an active member "
            "of this service team"
        )
    }

    validate_assignment.assert_called_once()
    record_pending.assert_not_called()


def test_execute_turn_confirms_stored_service_assignment(
    monkeypatch,
    authorized_client,
):
    pending = Mock()
    pending.church_id = 7
    pending.action_request_id = (
        "77777777-8888-4999-8aaa-bbbbbbbbbbbb"
    )
    pending.source_message_id = (
        "aaaaaaaa-2222-3333-4444-555555555555"
    )
    pending.arguments = {
        "event_id": 10,
        "group_id": 20,
        "church_membership_id": 30,
        "service_role": "Usher",
    }

    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            return {
                "conversation_id": CONVERSATION_ID,
                "user_message_id": (
                    "cccccccc-2222-3333-4444-555555555555"
                ),
                "confirmation": {
                    "action_name":
                    "service_assignment.create",
                },
            }

    pending_lookup = Mock(return_value=pending)
    execute_action = Mock(
        return_value={
            "name": "service_assignment.create",
            "result": {
                "assignment_id": 99,
                "church_id": 7,
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
        "_trusted_church_intelligence_context",
        Mock(return_value={"church_id": 7}),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_service_assignment",
        pending_lookup,
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
            "content": "Yes, assign them.",
            "request_id": REQUEST_ID,
            "church_id": 7,
        },
    )

    assert response.status_code == 200

    assert execute_action.call_count == 1
    kwargs = execute_action.call_args.kwargs

    assert kwargs["user_id"] == 123
    assert kwargs["request_id"] == (
        pending.action_request_id
    )
    assert kwargs["source_message_id"] == (
        pending.source_message_id
    )
    assert kwargs["church_id"] == 7
    assert kwargs["pending_action"] is pending

    # Execution target comes entirely from durable
    # server-owned pending state.
    assert kwargs["action"] == {
        "name": "service_assignment.create",
        "arguments": pending.arguments,
    }


def test_execute_turn_service_assignment_confirmation_fails_closed_for_other_church(
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
                    "cccccccc-2222-3333-4444-555555555555"
                ),
                "confirmation": {
                    "action_name":
                    "service_assignment.create",
                },
            }

    pending_lookup = Mock(return_value=None)
    execute_action = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "_trusted_church_intelligence_context",
        Mock(return_value={"church_id": 8}),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_service_assignment",
        pending_lookup,
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
            "content": "Yes.",
            "request_id": REQUEST_ID,
            "church_id": 8,
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "service_assignment.create requires "
            "trusted pending confirmation"
        )
    }

    # Lookup is explicitly bound to the currently trusted
    # Church Space. A pending action from another church
    # cannot authorize execution here.
    assert pending_lookup.call_args_list[-1].kwargs[
        "church_id"
    ] == 8

    execute_action.assert_not_called()


def test_execute_turn_service_assignment_confirmation_ignores_new_action_target(
    monkeypatch,
    authorized_client,
):
    pending = Mock()
    pending.church_id = 7
    pending.action_request_id = (
        "77777777-8888-4999-8aaa-bbbbbbbbbbbb"
    )
    pending.source_message_id = (
        "aaaaaaaa-2222-3333-4444-555555555555"
    )
    pending.arguments = {
        "event_id": 10,
        "group_id": 20,
        "church_membership_id": 30,
        "service_role": "Usher",
    }

    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            # Even if the AI response tries to attach a new
            # action target during confirmation, the route
            # must execute the durable pending target only.
            return {
                "conversation_id": CONVERSATION_ID,
                "user_message_id": (
                    "cccccccc-2222-3333-4444-555555555555"
                ),
                "confirmation": {
                    "action_name":
                    "service_assignment.create",
                },
                "action": {
                    "name": "service_assignment.create",
                    "arguments": {
                        "event_id": 999,
                        "group_id": 999,
                        "church_membership_id": 999,
                        "service_role": "Pastor",
                    },
                },
            }

    execute_action = Mock(
        return_value={
            "name": "service_assignment.create",
            "result": {"assignment_id": 99},
        }
    )

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "_trusted_church_intelligence_context",
        Mock(return_value={"church_id": 7}),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_service_assignment",
        Mock(return_value=pending),
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
            "content": "Yes.",
            "request_id": REQUEST_ID,
            "church_id": 7,
        },
    )

    assert response.status_code == 200

    kwargs = execute_action.call_args.kwargs

    assert kwargs["action"]["arguments"] == {
        "event_id": 10,
        "group_id": 20,
        "church_membership_id": 30,
        "service_role": "Usher",
    }

    assert kwargs["action"]["arguments"]["event_id"] != 999


def test_execute_turn_records_pending_service_assignment_status_update(
    monkeypatch,
    authorized_client,
):
    response_payload = {
        "conversation_id": CONVERSATION_ID,
        "user_message_id": (
            "dddddddd-2222-3333-4444-555555555555"
        ),
        "action": {
            "name": "service_assignment.update_status",
            "arguments": {
                "event_id": 10,
                "assignment_id": 40,
                "status": "confirmed",
            },
        },
        "prompt": "Confirm this service assignment?",
    }

    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            return response_payload

    validate_update = Mock()
    record_pending = Mock()
    execute_action = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "_trusted_church_intelligence_context",
        Mock(return_value={"church_id": 7}),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "validate_service_assignment_status_update_for_user",
        validate_update,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_service_assignment_status_update",
        Mock(return_value=None),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "record_pending_service_assignment_status_update",
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
            "content": "Confirm this assignment.",
            "request_id": REQUEST_ID,
            "church_id": 7,
        },
    )

    assert response.status_code == 200
    assert response.json() == response_payload

    validate_update.assert_called_once()
    validation_kwargs = validate_update.call_args.kwargs

    assert validation_kwargs["church_id"] == 7
    assert validation_kwargs["event_id"] == 10
    assert validation_kwargs["assignment_id"] == 40
    assert validation_kwargs["assignment_status"] == "confirmed"

    record_pending.assert_called_once()
    pending_kwargs = record_pending.call_args.kwargs

    assert pending_kwargs["user_id"] == 123
    assert pending_kwargs["conversation_id"] == CONVERSATION_ID
    assert pending_kwargs["church_id"] == 7
    assert pending_kwargs["arguments"] == {
        "event_id": 10,
        "assignment_id": 40,
        "status": "confirmed",
    }
    assert pending_kwargs["source_message_id"] == (
        "dddddddd-2222-3333-4444-555555555555"
    )
    assert isinstance(
        pending_kwargs["action_request_id"],
        str,
    )
    assert pending_kwargs["action_request_id"]

    execute_action.assert_not_called()


def test_execute_turn_status_confirmation_uses_stored_target(
    monkeypatch,
    authorized_client,
):
    pending = Mock()
    pending.church_id = 7
    pending.action_request_id = (
        "77777777-8888-4999-8aaa-bbbbbbbbbbbb"
    )
    pending.source_message_id = (
        "dddddddd-2222-3333-4444-555555555555"
    )
    pending.arguments = {
        "event_id": 10,
        "assignment_id": 40,
        "status": "confirmed",
    }

    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            return {
                "conversation_id": CONVERSATION_ID,
                "user_message_id": (
                    "eeeeeeee-2222-3333-4444-555555555555"
                ),
                "confirmation": {
                    "action_name":
                    "service_assignment.update_status",
                },
                # Malicious/stale fresh target must be ignored.
                "action": {
                    "name": "service_assignment.update_status",
                    "arguments": {
                        "event_id": 999,
                        "assignment_id": 999,
                        "status": "cancelled",
                    },
                },
            }

    execute_action = Mock(
        return_value={
            "name": "service_assignment.update_status",
            "status": "completed",
            "result": {
                "assignment_id": 40,
                "status": "confirmed",
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
        "_trusted_church_intelligence_context",
        Mock(return_value={"church_id": 7}),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_service_assignment_status_update",
        Mock(return_value=pending),
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
            "content": "Yes, confirm it.",
            "request_id": REQUEST_ID,
            "church_id": 7,
        },
    )

    assert response.status_code == 200

    execute_action.assert_called_once()
    kwargs = execute_action.call_args.kwargs

    assert kwargs["request_id"] == pending.action_request_id
    assert kwargs["source_message_id"] == (
        pending.source_message_id
    )
    assert kwargs["church_id"] == 7
    assert kwargs["pending_action"] is pending

    assert kwargs["action"] == {
        "name": "service_assignment.update_status",
        "arguments": {
            "event_id": 10,
            "assignment_id": 40,
            "status": "confirmed",
        },
    }

    assert kwargs["action"]["arguments"]["assignment_id"] != 999
    assert kwargs["action"]["arguments"]["status"] != "cancelled"


def test_execute_turn_status_confirmation_fails_for_other_church(
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
                    "eeeeeeee-2222-3333-4444-555555555555"
                ),
                "confirmation": {
                    "action_name":
                    "service_assignment.update_status",
                },
            }

    pending_lookup = Mock(return_value=None)
    execute_action = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XynAssistClient",
        FakeXynAssistClient,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "_trusted_church_intelligence_context",
        Mock(return_value={"church_id": 8}),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_service_assignment_status_update",
        pending_lookup,
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
            "content": "Yes.",
            "request_id": REQUEST_ID,
            "church_id": 8,
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "service_assignment.update_status requires "
            "trusted pending confirmation"
        )
    }

    assert pending_lookup.call_args.kwargs["church_id"] == 8
    execute_action.assert_not_called()


def test_execute_turn_records_pending_service_assignment_reassignment(
    monkeypatch,
    authorized_client,
):
    response_payload = {
        "conversation_id": CONVERSATION_ID,
        "user_message_id": (
            "f1111111-2222-3333-4444-555555555555"
        ),
        "action": {
            "name": "service_assignment.reassign",
            "arguments": {
                "event_id": 10,
                "assignment_id": 40,
                "group_id": 21,
                "church_membership_id": 31,
                "service_role": "Greeter",
            },
        },
        "prompt": "Confirm this service reassignment?",
    }

    class FakeXynAssistClient:
        async def execute_conversation_turn(self, **kwargs):
            return response_payload

    validate_reassignment = Mock()
    record_pending = Mock()
    execute_action = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations.XynAssistClient",
        FakeXynAssistClient,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "_trusted_church_intelligence_context",
        Mock(return_value={"church_id": 7}),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "validate_service_assignment_reassignment_for_user",
        validate_reassignment,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_service_assignment_reassignment",
        Mock(return_value=None),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "record_pending_service_assignment_reassignment",
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
            "content": "Reassign this volunteer.",
            "request_id": REQUEST_ID,
            "church_id": 7,
        },
    )

    assert response.status_code == 200
    assert response.json() == response_payload

    validate_reassignment.assert_called_once()
    validation_kwargs = validate_reassignment.call_args.kwargs

    assert validation_kwargs["church_id"] == 7
    assert validation_kwargs["event_id"] == 10
    assert validation_kwargs["assignment_id"] == 40
    assert validation_kwargs["group_id"] == 21
    assert validation_kwargs["church_membership_id"] == 31
    assert validation_kwargs["service_role"] == "Greeter"

    record_pending.assert_called_once()
    pending_kwargs = record_pending.call_args.kwargs

    assert pending_kwargs["user_id"] == 123
    assert pending_kwargs["conversation_id"] == CONVERSATION_ID
    assert pending_kwargs["church_id"] == 7
    assert pending_kwargs["arguments"] == {
        "event_id": 10,
        "assignment_id": 40,
        "group_id": 21,
        "church_membership_id": 31,
        "service_role": "Greeter",
    }
    assert pending_kwargs["source_message_id"] == (
        "f1111111-2222-3333-4444-555555555555"
    )
    assert isinstance(pending_kwargs["action_request_id"], str)
    assert pending_kwargs["action_request_id"]

    execute_action.assert_not_called()


def test_execute_turn_reassignment_confirmation_uses_stored_target(
    monkeypatch,
    authorized_client,
):
    pending = Mock()
    pending.church_id = 7
    pending.action_request_id = (
        "88888888-9999-4aaa-8bbb-cccccccccccc"
    )
    pending.source_message_id = (
        "f1111111-2222-3333-4444-555555555555"
    )
    pending.arguments = {
        "event_id": 10,
        "assignment_id": 40,
        "group_id": 21,
        "church_membership_id": 31,
        "service_role": "Greeter",
    }

    class FakeXynAssistClient:
        async def execute_conversation_turn(self, **kwargs):
            return {
                "conversation_id": CONVERSATION_ID,
                "user_message_id": (
                    "f2222222-2222-3333-4444-555555555555"
                ),
                "confirmation": {
                    "action_name": "service_assignment.reassign",
                },
                # Malicious/stale fresh target must be ignored.
                "action": {
                    "name": "service_assignment.reassign",
                    "arguments": {
                        "event_id": 999,
                        "assignment_id": 999,
                        "group_id": 999,
                        "church_membership_id": 999,
                        "service_role": "Malicious",
                    },
                },
            }

    execute_action = Mock(
        return_value={
            "name": "service_assignment.reassign",
            "status": "completed",
            "result": {
                "original_assignment_id": 40,
                "original_status": "cancelled",
                "replacement_assignment_id": 41,
                "status": "assigned",
            },
        }
    )

    monkeypatch.setattr(
        "api.routes.faith_conversations.XynAssistClient",
        FakeXynAssistClient,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "_trusted_church_intelligence_context",
        Mock(return_value={"church_id": 7}),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_service_assignment_reassignment",
        Mock(return_value=pending),
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
            "content": "Yes, reassign them.",
            "request_id": REQUEST_ID,
            "church_id": 7,
        },
    )

    assert response.status_code == 200

    execute_action.assert_called_once()
    kwargs = execute_action.call_args.kwargs

    assert kwargs["request_id"] == pending.action_request_id
    assert kwargs["source_message_id"] == pending.source_message_id
    assert kwargs["church_id"] == 7
    assert kwargs["pending_action"] is pending

    assert kwargs["action"] == {
        "name": "service_assignment.reassign",
        "arguments": {
            "event_id": 10,
            "assignment_id": 40,
            "group_id": 21,
            "church_membership_id": 31,
            "service_role": "Greeter",
        },
    }

    assert kwargs["action"]["arguments"]["assignment_id"] != 999
    assert kwargs["action"]["arguments"]["group_id"] != 999
    assert (
        kwargs["action"]["arguments"]["church_membership_id"]
        != 999
    )
    assert kwargs["action"]["arguments"]["service_role"] != "Malicious"


def test_execute_turn_reassignment_confirmation_fails_for_other_church(
    monkeypatch,
    authorized_client,
):
    class FakeXynAssistClient:
        async def execute_conversation_turn(self, **kwargs):
            return {
                "conversation_id": CONVERSATION_ID,
                "user_message_id": (
                    "f2222222-2222-3333-4444-555555555555"
                ),
                "confirmation": {
                    "action_name": "service_assignment.reassign",
                },
            }

    pending_lookup = Mock(return_value=None)
    execute_action = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations.XynAssistClient",
        FakeXynAssistClient,
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "_trusted_church_intelligence_context",
        Mock(return_value={"church_id": 8}),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_service_assignment_reassignment",
        pending_lookup,
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
            "content": "Yes.",
            "request_id": REQUEST_ID,
            "church_id": 8,
        },
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": (
            "service_assignment.reassign requires "
            "trusted pending confirmation"
        )
    }

    assert pending_lookup.call_args.kwargs["church_id"] == 8
    execute_action.assert_not_called()
