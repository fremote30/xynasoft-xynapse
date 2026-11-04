from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from api.models.conversation_pending_memory_action import (
    ConversationPendingMemoryAction,
)
from api.services.conversation_pending_memory_actions import (
    ConversationPendingMemoryActionError,
    MEMORY_FORGET_ACTION,
    consume_pending_memory_forget,
    get_pending_memory_forget,
    record_pending_memory_forget,
)


CONVERSATION_ID = (
    "11111111-2222-4333-8444-555555555555"
)

SOURCE_MESSAGE_ID = (
    "aaaaaaaa-2222-4333-8444-555555555555"
)

ACTION_REQUEST_ID = (
    "bbbbbbbb-2222-4333-8444-555555555555"
)


def make_db(*, existing=None):
    db = Mock()

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = existing

    return db, query


def test_record_pending_memory_forget_binds_exact_state():
    db, query = make_db()

    pending = record_pending_memory_forget(
        db=db,
        user_id=123,
        conversation_id=CONVERSATION_ID,
        memory_type="preference",
        memory_key="response_style",
        source_message_id=SOURCE_MESSAGE_ID,
        action_request_id=ACTION_REQUEST_ID,
    )

    assert isinstance(
        pending,
        ConversationPendingMemoryAction,
    )
    assert pending.user_id == 123
    assert pending.conversation_id == CONVERSATION_ID
    assert pending.action_name == MEMORY_FORGET_ACTION
    assert pending.memory_type == "preference"
    assert pending.memory_key == "response_style"
    assert pending.source_message_id == SOURCE_MESSAGE_ID
    assert pending.action_request_id == ACTION_REQUEST_ID

    db.query.assert_called_once_with(
        ConversationPendingMemoryAction
    )
    assert query.filter.call_count == 2
    db.add.assert_called_once_with(pending)
    db.flush.assert_called_once_with()


def test_new_proposal_replaces_entire_pending_identity():
    existing = SimpleNamespace(
        user_id=123,
        conversation_id=CONVERSATION_ID,
        action_name="old.action",
        memory_type="old_type",
        memory_key="old_key",
        source_message_id="old-message",
        action_request_id=(
            "cccccccc-2222-4333-8444-555555555555"
        ),
    )

    db, _ = make_db(existing=existing)

    result = record_pending_memory_forget(
        db=db,
        user_id=123,
        conversation_id=CONVERSATION_ID,
        memory_type="user_fact",
        memory_key="preferred_translation",
        source_message_id=SOURCE_MESSAGE_ID,
        action_request_id=ACTION_REQUEST_ID,
    )

    assert result is existing
    assert existing.action_name == MEMORY_FORGET_ACTION
    assert existing.memory_type == "user_fact"
    assert (
        existing.memory_key
        == "preferred_translation"
    )
    assert (
        existing.source_message_id
        == SOURCE_MESSAGE_ID
    )
    assert (
        existing.action_request_id
        == ACTION_REQUEST_ID
    )

    db.add.assert_not_called()
    db.flush.assert_called_once_with()


def test_get_pending_preserves_stable_action_request_id():
    existing = SimpleNamespace(
        user_id=123,
        conversation_id=CONVERSATION_ID,
        action_name=MEMORY_FORGET_ACTION,
        memory_type="preference",
        memory_key="response_style",
        source_message_id=SOURCE_MESSAGE_ID,
        action_request_id=ACTION_REQUEST_ID,
    )

    db, query = make_db(existing=existing)

    result = get_pending_memory_forget(
        db=db,
        user_id=123,
        conversation_id=CONVERSATION_ID,
    )

    assert result is existing
    assert result.action_request_id == ACTION_REQUEST_ID

    db.query.assert_called_once_with(
        ConversationPendingMemoryAction
    )
    assert query.filter.call_count == 2


def test_get_pending_isolated_by_authenticated_user():
    db, query = make_db(existing=None)

    result = get_pending_memory_forget(
        db=db,
        user_id=456,
        conversation_id=CONVERSATION_ID,
    )

    assert result is None

    db.query.assert_called_once_with(
        ConversationPendingMemoryAction
    )
    assert query.filter.call_count == 2


def test_get_pending_fails_closed_for_malformed_state():
    existing = SimpleNamespace(
        user_id=123,
        conversation_id=CONVERSATION_ID,
        action_name=MEMORY_FORGET_ACTION,
        memory_type="preference",
        memory_key="response_style",
        source_message_id=SOURCE_MESSAGE_ID,
        action_request_id="",
    )

    db, _ = make_db(existing=existing)

    assert (
        get_pending_memory_forget(
            db=db,
            user_id=123,
            conversation_id=CONVERSATION_ID,
        )
        is None
    )


def test_consume_removes_pending_state_without_commit():
    pending = SimpleNamespace()
    db = Mock()

    consume_pending_memory_forget(
        db=db,
        pending=pending,
    )

    db.delete.assert_called_once_with(pending)
    db.flush.assert_called_once_with()
    db.commit.assert_not_called()


@pytest.mark.parametrize(
    (
        "field",
        "value",
        "message",
    ),
    [
        (
            "conversation_id",
            "",
            "Conversation is invalid",
        ),
        (
            "memory_type",
            "",
            "Memory type is invalid",
        ),
        (
            "memory_key",
            "",
            "Memory key is invalid",
        ),
        (
            "source_message_id",
            "",
            "confirmation source",
        ),
        (
            "action_request_id",
            "",
            "Memory action request is invalid",
        ),
    ],
)
def test_record_pending_rejects_invalid_required_state(
    field,
    value,
    message,
):
    db = Mock()

    arguments = {
        "db": db,
        "user_id": 123,
        "conversation_id": CONVERSATION_ID,
        "memory_type": "preference",
        "memory_key": "response_style",
        "source_message_id": SOURCE_MESSAGE_ID,
        "action_request_id": ACTION_REQUEST_ID,
    }
    arguments[field] = value

    with pytest.raises(
        ConversationPendingMemoryActionError,
        match=message,
    ):
        record_pending_memory_forget(**arguments)

    db.query.assert_not_called()
    db.add.assert_not_called()
    db.flush.assert_not_called()


def test_get_pending_rejects_invalid_conversation_without_query():
    db = Mock()

    assert (
        get_pending_memory_forget(
            db=db,
            user_id=123,
            conversation_id="",
        )
        is None
    )

    db.query.assert_not_called()
