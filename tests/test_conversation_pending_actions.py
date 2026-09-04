from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from api.models.conversation_pending_action import (
    ConversationPendingAction,
)
from api.services.conversation_pending_actions import (
    ConversationPendingActionError,
    SERMON_DELETE_ACTION,
    SERMON_RESOURCE,
    record_pending_sermon_delete,
)


CONVERSATION_ID = (
    "11111111-2222-3333-4444-555555555555"
)

SOURCE_MESSAGE_ID = (
    "aaaaaaaa-2222-3333-4444-555555555555"
)


def make_db(
    *,
    existing=None,
):
    db = Mock()

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = existing

    return db, query


def test_record_pending_delete_binds_authenticated_context():
    db, query = make_db()

    pending = record_pending_sermon_delete(
        db=db,
        user_id=123,
        conversation_id=CONVERSATION_ID,
        sermon_id=42,
        source_message_id=SOURCE_MESSAGE_ID,
    )

    assert isinstance(
        pending,
        ConversationPendingAction,
    )

    assert pending.user_id == 123
    assert pending.conversation_id == CONVERSATION_ID
    assert pending.action_name == SERMON_DELETE_ACTION
    assert pending.resource_type == SERMON_RESOURCE
    assert pending.resource_id == 42
    assert pending.source_message_id == SOURCE_MESSAGE_ID

    db.query.assert_called_once_with(
        ConversationPendingAction
    )

    assert query.filter.call_count == 2

    db.add.assert_called_once_with(
        pending
    )
    db.commit.assert_called_once_with()


def test_record_pending_delete_replaces_existing_binding():
    existing = SimpleNamespace(
        user_id=123,
        conversation_id=CONVERSATION_ID,
        action_name="old.action",
        resource_type="old_resource",
        resource_id=11,
        source_message_id="old-message",
    )

    db, _ = make_db(
        existing=existing,
    )

    result = record_pending_sermon_delete(
        db=db,
        user_id=123,
        conversation_id=CONVERSATION_ID,
        sermon_id=84,
        source_message_id=SOURCE_MESSAGE_ID,
    )

    assert result is existing

    assert existing.action_name == SERMON_DELETE_ACTION
    assert existing.resource_type == SERMON_RESOURCE
    assert existing.resource_id == 84
    assert existing.source_message_id == SOURCE_MESSAGE_ID

    db.add.assert_not_called()
    db.commit.assert_called_once_with()


@pytest.mark.parametrize(
    "sermon_id",
    [
        None,
        0,
        -1,
        True,
    ],
)
def test_record_pending_delete_requires_saved_sermon(
    sermon_id,
):
    db = Mock()

    with pytest.raises(
        ConversationPendingActionError,
        match="saved sermon",
    ):
        record_pending_sermon_delete(
            db=db,
            user_id=123,
            conversation_id=CONVERSATION_ID,
            sermon_id=sermon_id,
            source_message_id=SOURCE_MESSAGE_ID,
        )

    db.query.assert_not_called()
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize(
    "conversation_id",
    [
        "",
        "   ",
        "x" * 37,
    ],
)
def test_record_pending_delete_rejects_invalid_conversation(
    conversation_id,
):
    db = Mock()

    with pytest.raises(
        ConversationPendingActionError,
        match="Conversation is invalid",
    ):
        record_pending_sermon_delete(
            db=db,
            user_id=123,
            conversation_id=conversation_id,
            sermon_id=42,
            source_message_id=SOURCE_MESSAGE_ID,
        )

    db.query.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize(
    "source_message_id",
    [
        "",
        "   ",
        "x" * 256,
    ],
)
def test_record_pending_delete_rejects_invalid_source(
    source_message_id,
):
    db = Mock()

    with pytest.raises(
        ConversationPendingActionError,
        match="confirmation source",
    ):
        record_pending_sermon_delete(
            db=db,
            user_id=123,
            conversation_id=CONVERSATION_ID,
            sermon_id=42,
            source_message_id=source_message_id,
        )

    db.query.assert_not_called()
    db.commit.assert_not_called()


def test_record_pending_delete_normalizes_identifiers():
    db, _ = make_db()

    pending = record_pending_sermon_delete(
        db=db,
        user_id=123,
        conversation_id=(
            f"  {CONVERSATION_ID}  "
        ),
        sermon_id=42,
        source_message_id=(
            f"  {SOURCE_MESSAGE_ID}  "
        ),
    )

    assert pending.conversation_id == CONVERSATION_ID
    assert pending.source_message_id == SOURCE_MESSAGE_ID


def test_get_pending_delete_returns_exact_binding():
    from api.services.conversation_pending_actions import (
        get_pending_sermon_delete,
    )

    existing = SimpleNamespace(
        user_id=123,
        conversation_id=CONVERSATION_ID,
        action_name=SERMON_DELETE_ACTION,
        resource_type=SERMON_RESOURCE,
        resource_id=42,
        source_message_id=SOURCE_MESSAGE_ID,
    )

    db, _ = make_db(
        existing=existing,
    )

    result = get_pending_sermon_delete(
        db=db,
        user_id=123,
        conversation_id=CONVERSATION_ID,
        sermon_id=42,
    )

    assert result is existing


def test_get_pending_delete_rejects_different_sermon():
    from api.services.conversation_pending_actions import (
        get_pending_sermon_delete,
    )

    existing = SimpleNamespace(
        action_name=SERMON_DELETE_ACTION,
        resource_type=SERMON_RESOURCE,
        resource_id=42,
    )

    db, _ = make_db(
        existing=existing,
    )

    result = get_pending_sermon_delete(
        db=db,
        user_id=123,
        conversation_id=CONVERSATION_ID,
        sermon_id=84,
    )

    assert result is None


@pytest.mark.parametrize(
    ("action_name", "resource_type"),
    [
        ("sermon.update", SERMON_RESOURCE),
        (SERMON_DELETE_ACTION, "prayer"),
    ],
)
def test_get_pending_delete_rejects_wrong_pending_type(
    action_name,
    resource_type,
):
    from api.services.conversation_pending_actions import (
        get_pending_sermon_delete,
    )

    existing = SimpleNamespace(
        action_name=action_name,
        resource_type=resource_type,
        resource_id=42,
    )

    db, _ = make_db(
        existing=existing,
    )

    result = get_pending_sermon_delete(
        db=db,
        user_id=123,
        conversation_id=CONVERSATION_ID,
        sermon_id=42,
    )

    assert result is None


@pytest.mark.parametrize(
    "sermon_id",
    [
        None,
        0,
        -1,
        True,
    ],
)
def test_get_pending_delete_requires_saved_current_sermon(
    sermon_id,
):
    from api.services.conversation_pending_actions import (
        get_pending_sermon_delete,
    )

    db = Mock()

    result = get_pending_sermon_delete(
        db=db,
        user_id=123,
        conversation_id=CONVERSATION_ID,
        sermon_id=sermon_id,
    )

    assert result is None
    db.query.assert_not_called()
