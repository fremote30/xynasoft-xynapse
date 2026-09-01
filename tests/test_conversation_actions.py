from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from api.services.conversation_actions import (
    ConversationActionContextError,
    UnsupportedConversationActionError,
    execute_conversation_action,
)


REQUEST_ID = (
    "11111111-2222-4333-8444-555555555555"
)

def test_sermon_save_uses_authenticated_user(
    monkeypatch,
):
    db = Mock()

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    save = Mock(
        return_value=SimpleNamespace(
            id=42,
        )
    )

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_for_user",
        save,
    )

    sermon_data = {
        "title": "Trust the Lord",
        "scripture": "Proverbs 3:5-6",
        "points": [],
    }

    result = execute_conversation_action(
        db=db,
        user_id=123,
            request_id=REQUEST_ID,
            source_message_id=(
                "aaaaaaaa-2222-3333-4444-555555555555"
            ),
        action={
            "name": "sermon.save",
            "arguments": {},
        },
        sermon_id=None,
        sermon_data=sermon_data,
    )

    save.assert_called_once_with(
        db=db,
        user_id=123,
        payload=sermon_data,
    )

    assert result == {
        "name": "sermon.save",
        "status": "completed",
        "result": {
            "sermon_id": 42,
        },
    }


def test_unknown_action_fails_closed(
    monkeypatch,
):
    save = Mock()

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_for_user",
        save,
    )

    with pytest.raises(
        UnsupportedConversationActionError
    ):
        execute_conversation_action(
            db=Mock(),
            user_id=123,
            request_id=REQUEST_ID,
            source_message_id=(
                "aaaaaaaa-2222-3333-4444-555555555555"
            ),
            action={
                "name": "sermon.delete",
                "arguments": {},
            },
            sermon_id=None,
            sermon_data={
                "title": "Sermon",
            },
        )

    save.assert_not_called()


def test_sermon_save_requires_sermon_context(
    monkeypatch,
):
    save = Mock()

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_for_user",
        save,
    )

    with pytest.raises(
        ConversationActionContextError
    ):
        execute_conversation_action(
            db=Mock(),
            user_id=123,
            request_id=REQUEST_ID,
            source_message_id=(
                "aaaaaaaa-2222-3333-4444-555555555555"
            ),
            action={
                "name": "sermon.save",
                "arguments": {},
            },
            sermon_id=None,
            sermon_data=None,
        )

    save.assert_not_called()


def test_sermon_save_rejects_existing_sermon_id(
    monkeypatch,
):
    save = Mock()

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_for_user",
        save,
    )

    with pytest.raises(
        ConversationActionContextError
    ):
        execute_conversation_action(
            db=Mock(),
            user_id=123,
            request_id=REQUEST_ID,
            source_message_id=(
                "aaaaaaaa-2222-3333-4444-555555555555"
            ),
            action={
                "name": "sermon.save",
                "arguments": {},
            },
            sermon_id=42,
            sermon_data={
                "title": "Existing Sermon",
            },
        )

    save.assert_not_called()


def test_sermon_save_rejects_nonempty_arguments(
    monkeypatch,
):
    save = Mock()

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_for_user",
        save,
    )

    with pytest.raises(
        ConversationActionContextError,
        match="does not accept arguments",
    ):
        execute_conversation_action(
            db=Mock(),
            user_id=123,
            request_id=REQUEST_ID,
            source_message_id=(
                "aaaaaaaa-2222-3333-4444-555555555555"
            ),
            action={
                "name": "sermon.save",
                "arguments": {
                    "user_id": 999,
                },
            },
            sermon_id=None,
            sermon_data={
                "title": "Sermon",
            },
        )

    save.assert_not_called()
