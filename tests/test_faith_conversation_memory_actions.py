from __future__ import annotations

from unittest.mock import Mock
from uuid import UUID

from fastapi.testclient import TestClient

from api.core.dependencies import get_current_user, get_db
from api.models.user import User
from main import app


CONVERSATION_ID = "11111111-2222-3333-4444-555555555555"
REQUEST_ID = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
SOURCE_MESSAGE_ID = "99999999-8888-7777-6666-555555555555"


def _authorized_client(
    monkeypatch,
    *,
    turn_response,
    execute_memory_response=None,
):
    db = Mock()

    user = Mock(spec=User)
    user.id = 123

    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            return turn_response

        async def execute_memory_action(
            self,
            **kwargs,
        ):
            execute_memory_action.calls.append(kwargs)

            if execute_memory_response is None:
                return {
                    "name": kwargs["action_name"],
                    "status": "completed",
                    "result": {},
                }

            return execute_memory_response

    execute_memory_action = Mock()
    execute_memory_action.calls = []

    monkeypatch.setattr(
        "api.routes.faith_conversations.XynAssistClient",
        FakeXynAssistClient,
    )

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
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "XYNASSIST_ENABLED",
        True,
    )

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db

    client = TestClient(app)

    return client, db, execute_memory_action


def _post_turn(client):
    return client.post(
        "/api/v1/faith/conversations/"
        f"{CONVERSATION_ID}/turns",
        json={
            "content": "Please update your memory.",
            "request_id": REQUEST_ID,
        },
    )


def test_memory_remember_executes_immediately_without_confirmation(
    monkeypatch,
):
    turn_response = {
        "conversation_id": CONVERSATION_ID,
        "user_message_id": SOURCE_MESSAGE_ID,
        "action": {
            "name": "memory.remember",
            "arguments": {
                "memory_type": "preference",
                "key": "sermon_tone",
                "value": "pastoral",
            },
        },
    }

    executed_response = {
        "name": "memory.remember",
        "status": "completed",
        "result": {
            "memory_type": "preference",
            "key": "sermon_tone",
        },
    }

    client, _, calls = _authorized_client(
        monkeypatch,
        turn_response=turn_response,
        execute_memory_response=executed_response,
    )

    try:
        response = _post_turn(client)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert len(calls.calls) == 1

    call = calls.calls[0]

    assert call["external_user_id"] == "123"
    assert call["action_name"] == "memory.remember"
    assert call["arguments"] == {
        "memory_type": "preference",
        "key": "sermon_tone",
        "value": "pastoral",
    }
    assert call["trusted_confirmed"] is False

    # Action execution has its own stable UUID identity rather
    # than reusing the conversation-turn request identifier.
    UUID(call["request_id"])
    assert call["request_id"] != REQUEST_ID

    assert response.json()["action"] == executed_response


def test_memory_remember_action_identity_is_deterministic(
    monkeypatch,
):
    from api.routes.faith_conversations import (
        _memory_action_request_id,
    )

    first = _memory_action_request_id(
        user_id=123,
        conversation_id=CONVERSATION_ID,
        turn_request_id=REQUEST_ID,
        action_name="memory.remember",
    )

    second = _memory_action_request_id(
        user_id=123,
        conversation_id=CONVERSATION_ID,
        turn_request_id=REQUEST_ID,
        action_name="memory.remember",
    )

    changed_turn = _memory_action_request_id(
        user_id=123,
        conversation_id=CONVERSATION_ID,
        turn_request_id=(
            "bbbbbbbb-cccc-dddd-eeee-ffffffffffff"
        ),
        action_name="memory.remember",
    )

    assert first == second
    assert first != REQUEST_ID
    assert first != changed_turn
    UUID(first)


def test_memory_remember_rejects_confirmation_prompt(
    monkeypatch,
):
    turn_response = {
        "conversation_id": CONVERSATION_ID,
        "user_message_id": SOURCE_MESSAGE_ID,
        "action": {
            "name": "memory.remember",
            "arguments": {
                "memory_type": "user_fact",
                "key": "preferred_language",
                "value": "English",
            },
        },
        "prompt": "Confirm this?",
    }

    client, _, calls = _authorized_client(
        monkeypatch,
        turn_response=turn_response,
    )

    try:
        response = _post_turn(client)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert calls.calls == []


def test_memory_forget_records_pending_without_remote_execution(
    monkeypatch,
):
    turn_response = {
        "conversation_id": CONVERSATION_ID,
        "user_message_id": SOURCE_MESSAGE_ID,
        "action": {
            "name": "memory.forget",
            "arguments": {
                "memory_type": "preference",
                "key": "sermon_tone",
            },
        },
        "prompt": "Should I forget that preference?",
    }

    record_pending = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "record_pending_memory_forget",
        record_pending,
    )

    client, db, calls = _authorized_client(
        monkeypatch,
        turn_response=turn_response,
    )

    try:
        response = _post_turn(client)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == turn_response
    assert calls.calls == []

    record_pending.assert_called_once()

    call = record_pending.call_args.kwargs

    assert call["db"] is db
    assert call["user_id"] == 123
    assert call["conversation_id"] == CONVERSATION_ID
    assert call["memory_type"] == "preference"
    assert call["memory_key"] == "sermon_tone"
    assert call["source_message_id"] == SOURCE_MESSAGE_ID

    UUID(call["action_request_id"])
    assert call["action_request_id"] != REQUEST_ID

    db.commit.assert_called_once()


def test_memory_forget_rejects_missing_confirmation_prompt(
    monkeypatch,
):
    turn_response = {
        "conversation_id": CONVERSATION_ID,
        "user_message_id": SOURCE_MESSAGE_ID,
        "action": {
            "name": "memory.forget",
            "arguments": {
                "memory_type": "preference",
                "key": "sermon_tone",
            },
        },
    }

    record_pending = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "record_pending_memory_forget",
        record_pending,
    )

    client, _, calls = _authorized_client(
        monkeypatch,
        turn_response=turn_response,
    )

    try:
        response = _post_turn(client)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    record_pending.assert_not_called()
    assert calls.calls == []


def test_memory_action_rejects_extra_confirmation_argument(
    monkeypatch,
):
    turn_response = {
        "conversation_id": CONVERSATION_ID,
        "user_message_id": SOURCE_MESSAGE_ID,
        "action": {
            "name": "memory.forget",
            "arguments": {
                "memory_type": "preference",
                "key": "sermon_tone",
                "confirmed": True,
            },
        },
        "prompt": "Should I forget that preference?",
    }

    record_pending = Mock()

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "record_pending_memory_forget",
        record_pending,
    )

    client, _, calls = _authorized_client(
        monkeypatch,
        turn_response=turn_response,
    )

    try:
        response = _post_turn(client)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    record_pending.assert_not_called()
    assert calls.calls == []


def test_memory_action_rejects_unknown_memory_type(
    monkeypatch,
):
    turn_response = {
        "conversation_id": CONVERSATION_ID,
        "user_message_id": SOURCE_MESSAGE_ID,
        "action": {
            "name": "memory.remember",
            "arguments": {
                "memory_type": "pastoral_care",
                "key": "private_note",
                "value": "sensitive",
            },
        },
    }

    client, _, calls = _authorized_client(
        monkeypatch,
        turn_response=turn_response,
    )

    try:
        response = _post_turn(client)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert calls.calls == []


def test_memory_forget_pending_failure_rolls_back(
    monkeypatch,
):
    turn_response = {
        "conversation_id": CONVERSATION_ID,
        "user_message_id": SOURCE_MESSAGE_ID,
        "action": {
            "name": "memory.forget",
            "arguments": {
                "memory_type": "preference",
                "key": "sermon_tone",
            },
        },
        "prompt": "Should I forget that preference?",
    }

    def fail_pending(**kwargs):
        raise RuntimeError("database failure")

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "record_pending_memory_forget",
        fail_pending,
    )

    client, db, calls = _authorized_client(
        monkeypatch,
        turn_response=turn_response,
    )

    try:
        response = _post_turn(client)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500
    db.rollback.assert_called_once()
    assert calls.calls == []
