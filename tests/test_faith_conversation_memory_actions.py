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


def test_memory_forget_without_prompt_requires_pending_state(
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

    assert response.status_code == 422
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


def _pending_memory(
    *,
    memory_type="preference",
    memory_key="sermon_tone",
    action_request_id=(
        "12121212-3434-5656-7878-909090909090"
    ),
):
    pending = Mock()
    pending.action_name = "memory.forget"
    pending.memory_type = memory_type
    pending.memory_key = memory_key
    pending.source_message_id = SOURCE_MESSAGE_ID
    pending.action_request_id = action_request_id
    return pending


def test_memory_forget_confirmation_executes_trusted_pending_target(
    monkeypatch,
):
    action_request_id = (
        "12121212-3434-5656-7878-909090909090"
    )
    pending = _pending_memory(
        action_request_id=action_request_id,
    )

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
        "prompt": None,
    }

    executed_response = {
        "name": "memory.forget",
        "status": "completed",
        "result": {
            "memory_type": "preference",
            "key": "sermon_tone",
        },
    }

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_memory_forget",
        Mock(return_value=pending),
    )

    consume_pending = Mock()
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "consume_pending_memory_forget",
        consume_pending,
    )

    client, db, calls = _authorized_client(
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
    assert call["request_id"] == action_request_id
    assert call["action_name"] == "memory.forget"
    assert call["arguments"] == {
        "memory_type": "preference",
        "key": "sermon_tone",
    }
    assert call["trusted_confirmed"] is True

    consume_pending.assert_called_once_with(
        db=db,
        pending=pending,
    )
    db.commit.assert_called_once()
    assert response.json()["action"] == executed_response


def test_memory_forget_confirmation_exposes_only_pending_marker(
    monkeypatch,
):
    pending = _pending_memory()

    observed_context = {}

    class FakeXynAssistClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            observed_context.update(kwargs["context"])

            return {
                "conversation_id": CONVERSATION_ID,
                "user_message_id": SOURCE_MESSAGE_ID,
            }

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_memory_forget",
        Mock(return_value=pending),
    )
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
        "XYNASSIST_ENABLED",
        True,
    )

    db = Mock()
    user = Mock(spec=User)
    user.id = 123

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db

    client = TestClient(app)

    try:
        response = _post_turn(client)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert observed_context["pending_memory_action"] == (
        "memory.forget"
    )

    # Exact target and execution identity remain server-side.
    assert "memory_type" not in observed_context
    assert "memory_key" not in observed_context
    assert "action_request_id" not in observed_context


def test_memory_forget_confirmation_requires_pending_state(
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
        "prompt": None,
    }

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_memory_forget",
        Mock(return_value=None),
    )

    client, _, calls = _authorized_client(
        monkeypatch,
        turn_response=turn_response,
    )

    try:
        response = _post_turn(client)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert calls.calls == []


def test_memory_forget_confirmation_rejects_target_mismatch(
    monkeypatch,
):
    pending = _pending_memory(
        memory_type="preference",
        memory_key="sermon_tone",
    )

    turn_response = {
        "conversation_id": CONVERSATION_ID,
        "user_message_id": SOURCE_MESSAGE_ID,
        "action": {
            "name": "memory.forget",
            "arguments": {
                "memory_type": "user_fact",
                "key": "home_church",
            },
        },
        "prompt": None,
    }

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_memory_forget",
        Mock(return_value=pending),
    )

    consume_pending = Mock()
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "consume_pending_memory_forget",
        consume_pending,
    )

    client, db, calls = _authorized_client(
        monkeypatch,
        turn_response=turn_response,
    )

    try:
        response = _post_turn(client)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    assert calls.calls == []
    consume_pending.assert_not_called()
    db.commit.assert_not_called()


def test_memory_forget_remote_failure_preserves_pending(
    monkeypatch,
):
    from api.services.xynassist_client import XynAssistError

    pending = _pending_memory()

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
        "prompt": None,
    }

    class FailingXynAssistClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            return turn_response

        async def execute_memory_action(
            self,
            **kwargs,
        ):
            raise XynAssistError("remote failure")

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_memory_forget",
        Mock(return_value=pending),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "consume_pending_memory_forget",
        Mock(),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations.XynAssistClient",
        FailingXynAssistClient,
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
        "XYNASSIST_ENABLED",
        True,
    )

    db = Mock()
    user = Mock(spec=User)
    user.id = 123

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db

    client = TestClient(app)

    try:
        response = _post_turn(client)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_memory_forget_local_consume_failure_rolls_back(
    monkeypatch,
):
    pending = _pending_memory()

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
        "prompt": None,
    }

    def fail_consume(**kwargs):
        raise RuntimeError("local failure")

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_memory_forget",
        Mock(return_value=pending),
    )
    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "consume_pending_memory_forget",
        fail_consume,
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

    # Remote execution happened, but stable pending state is
    # retained by rollback so retry can replay the same action ID.
    assert len(calls.calls) == 1
    assert (
        calls.calls[0]["request_id"]
        == pending.action_request_id
    )
    assert calls.calls[0]["trusted_confirmed"] is True

    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_memory_forget_same_proposal_replay_preserves_action_id(
    monkeypatch,
):
    existing_action_request_id = (
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )

    pending = _pending_memory(
        memory_type="preference",
        memory_key="sermon_tone",
        action_request_id=existing_action_request_id,
    )
    pending.source_message_id = SOURCE_MESSAGE_ID

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
        "prompt": "Forget this memory?",
    }

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_memory_forget",
        Mock(return_value=pending),
    )

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

    assert response.status_code == 200
    assert calls.calls == []

    record_pending.assert_called_once()

    kwargs = record_pending.call_args.kwargs

    assert (
        kwargs["action_request_id"]
        == existing_action_request_id
    )
    assert kwargs["source_message_id"] == SOURCE_MESSAGE_ID


def test_memory_forget_new_proposal_replaces_action_id(
    monkeypatch,
):
    existing_action_request_id = (
        "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    )

    pending = _pending_memory(
        memory_type="preference",
        memory_key="sermon_tone",
        action_request_id=existing_action_request_id,
    )

    # Same logical target, but a different trusted proposal message
    # means this is a genuinely new proposal rather than a replay.
    pending.source_message_id = (
        "88888888-7777-6666-5555-444444444444"
    )

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
        "prompt": "Forget this memory?",
    }

    monkeypatch.setattr(
        "api.routes.faith_conversations."
        "get_pending_memory_forget",
        Mock(return_value=pending),
    )

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

    assert response.status_code == 200
    assert calls.calls == []

    record_pending.assert_called_once()

    kwargs = record_pending.call_args.kwargs

    assert (
        kwargs["action_request_id"]
        != existing_action_request_id
    )
    assert kwargs["source_message_id"] == SOURCE_MESSAGE_ID
