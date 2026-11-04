from types import SimpleNamespace
from unittest.mock import MagicMock, Mock

from sqlalchemy.exc import IntegrityError

import pytest

from api.models.conversation_action_execution import (
    ConversationActionExecution,
)
from api.models.conversation_pending_action import (
    ConversationPendingAction,
)

from api.services.sermon_persistence import (
    SermonNotFoundError,
)

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
                "name": "sermon.publish",
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

def test_sermon_update_uses_authenticated_user(
    monkeypatch,
):
    db = Mock()

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    update = Mock(
        return_value=SimpleNamespace(
            id=42,
        )
    )

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_update_for_user",
        update,
    )

    sermon_data = {
        "title": "Updated Sermon",
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
            "name": "sermon.update",
            "arguments": {},
        },
        sermon_id=42,
        sermon_data=sermon_data,
    )

    update.assert_called_once_with(
        db=db,
        user_id=123,
        sermon_id=42,
        payload=sermon_data,
    )

    db.commit.assert_called_once()

    assert result == {
        "name": "sermon.update",
        "status": "completed",
        "result": {
            "sermon_id": 42,
        },
    }


def test_sermon_update_requires_saved_sermon_id(
    monkeypatch,
):
    update = Mock()

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_update_for_user",
        update,
    )

    with pytest.raises(
        ConversationActionContextError,
        match="requires a saved sermon",
    ):
        execute_conversation_action(
            db=Mock(),
            user_id=123,
            request_id=REQUEST_ID,
            source_message_id=(
                "aaaaaaaa-2222-3333-4444-555555555555"
            ),
            action={
                "name": "sermon.update",
                "arguments": {},
            },
            sermon_id=None,
            sermon_data={
                "title": "Updated Sermon",
            },
        )

    update.assert_not_called()


def test_sermon_update_rejects_nonempty_arguments(
    monkeypatch,
):
    update = Mock()

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_update_for_user",
        update,
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
                "name": "sermon.update",
                "arguments": {
                    "sermon_id": 999,
                },
            },
            sermon_id=42,
            sermon_data={
                "title": "Updated Sermon",
            },
        )

    update.assert_not_called()


def test_execute_sermon_delete_uses_trusted_bound_sermon(
    monkeypatch,
):
    db = MagicMock()

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    delete = MagicMock(
        return_value=SimpleNamespace(
            id=42,
        )
    )

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_delete_for_user",
        delete,
    )

    result = execute_conversation_action(
        db=db,
        user_id=123,
        request_id=REQUEST_ID,
        source_message_id=(
            "aaaaaaaa-2222-3333-4444-555555555555"
        ),
        action={
            "name": "sermon.delete",
            "arguments": {},
        },
        # Browser/current resource context is deliberately
        # different. It must not become deletion authority.
        sermon_id=999,
        sermon_data=None,
        bound_sermon_id=42,
        pending_action=ConversationPendingAction(
            user_id=123,
            conversation_id=(
                "22222222-3333-4444-8555-666666666666"
            ),
            action_name="sermon.delete",
            resource_type="sermon",
            resource_id=42,
            source_message_id=(
                "aaaaaaaa-2222-3333-4444-555555555555"
            ),
        ),
    )

    delete.assert_called_once_with(
        db=db,
        user_id=123,
        sermon_id=42,
    )

    execution = None

    for call in db.add.call_args_list:
        candidate = call.args[0]

        if isinstance(
            candidate,
            ConversationActionExecution,
        ):
            execution = candidate

    assert execution is not None
    assert execution.action_name == "sermon.delete"
    assert execution.result == {
        "sermon_id": 42,
    }

    db.commit.assert_called_once()

    assert result == {
        "name": "sermon.delete",
        "status": "completed",
        "result": {
            "sermon_id": 42,
        },
    }


@pytest.mark.parametrize(
    "bound_sermon_id",
    [
        None,
        0,
        -1,
        True,
    ],
)
def test_execute_sermon_delete_requires_trusted_binding(
    monkeypatch,
    bound_sermon_id,
):
    db = MagicMock()

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    delete = MagicMock()

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_delete_for_user",
        delete,
    )

    with pytest.raises(
        ConversationActionContextError,
        match="trusted bound sermon",
    ):
        execute_conversation_action(
            db=db,
            user_id=123,
            request_id=REQUEST_ID,
            source_message_id=(
            "aaaaaaaa-2222-3333-4444-555555555555"
        ),
            action={
                "name": "sermon.delete",
                "arguments": {},
            },
            sermon_id=999,
            sermon_data=None,
            bound_sermon_id=bound_sermon_id,
        )

    delete.assert_not_called()
    db.commit.assert_not_called()


def test_execute_sermon_delete_fails_closed_when_not_owned(
    monkeypatch,
):
    db = MagicMock()

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    delete = MagicMock(
        side_effect=SermonNotFoundError(
            "Sermon not found"
        )
    )

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_delete_for_user",
        delete,
    )

    with pytest.raises(
        ConversationActionContextError,
        match="Sermon not found",
    ):
        execute_conversation_action(
            db=db,
            user_id=123,
            request_id=REQUEST_ID,
            source_message_id=(
            "aaaaaaaa-2222-3333-4444-555555555555"
        ),
            action={
                "name": "sermon.delete",
                "arguments": {},
            },
            sermon_id=999,
            sermon_data=None,
            bound_sermon_id=42,
            pending_action=ConversationPendingAction(
                user_id=123,
                conversation_id=(
                    "22222222-3333-4444-8555-666666666666"
                ),
                action_name="sermon.delete",
                resource_type="sermon",
                resource_id=42,
                source_message_id=(
                    "aaaaaaaa-2222-3333-4444-555555555555"
                ),
            ),
        )

    delete.assert_called_once_with(
        db=db,
        user_id=123,
        sermon_id=42,
    )

    db.commit.assert_not_called()


def _pending_sermon_delete(
    *,
    user_id=123,
    resource_id=42,
    action_name="sermon.delete",
    resource_type="sermon",
):
    return ConversationPendingAction(
        user_id=user_id,
        conversation_id=(
            "22222222-3333-4444-8555-666666666666"
        ),
        action_name=action_name,
        resource_type=resource_type,
        resource_id=resource_id,
        source_message_id=(
            "aaaaaaaa-2222-3333-4444-555555555555"
        ),
    )


def test_sermon_delete_consumes_pending_confirmation(
    monkeypatch,
):
    db = MagicMock()

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    pending = _pending_sermon_delete()

    delete_sermon = MagicMock(
        return_value=SimpleNamespace(id=42)
    )

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_delete_for_user",
        delete_sermon,
    )

    result = execute_conversation_action(
        db=db,
        user_id=123,
        request_id=REQUEST_ID,
        source_message_id=(
            "aaaaaaaa-2222-3333-4444-555555555555"
        ),
        action={
            "name": "sermon.delete",
            "arguments": {},
        },
        sermon_id=999,
        sermon_data=None,
        bound_sermon_id=42,
        pending_action=pending,
    )

    delete_sermon.assert_called_once_with(
        db=db,
        user_id=123,
        sermon_id=42,
    )

    db.delete.assert_called_once_with(pending)
    db.commit.assert_called_once()

    assert result == {
        "name": "sermon.delete",
        "status": "completed",
        "result": {
            "sermon_id": 42,
        },
    }


@pytest.mark.parametrize(
    "pending",
    [
        _pending_sermon_delete(user_id=999),
        _pending_sermon_delete(resource_id=84),
        _pending_sermon_delete(
            action_name="sermon.update"
        ),
        _pending_sermon_delete(
            resource_type="document"
        ),
        None,
    ],
)
def test_sermon_delete_rejects_untrusted_pending_confirmation(
    monkeypatch,
    pending,
):
    db = MagicMock()

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    delete_sermon = MagicMock()

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_delete_for_user",
        delete_sermon,
    )

    with pytest.raises(
        ConversationActionContextError,
        match="trusted pending confirmation",
    ):
        execute_conversation_action(
            db=db,
            user_id=123,
            request_id=REQUEST_ID,
            source_message_id=(
                "aaaaaaaa-2222-3333-4444-555555555555"
            ),
            action={
                "name": "sermon.delete",
                "arguments": {},
            },
            sermon_id=999,
            sermon_data=None,
            bound_sermon_id=42,
            pending_action=pending,
        )

    delete_sermon.assert_not_called()
    db.delete.assert_not_called()
    db.commit.assert_not_called()


def test_completed_sermon_delete_replays_without_pending_confirmation(
    monkeypatch,
):
    db = MagicMock()

    existing = SimpleNamespace(
        action_name="sermon.delete",
        status="completed",
        result={
            "sermon_id": 42,
        },
    )

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = existing

    delete_sermon = MagicMock()

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_delete_for_user",
        delete_sermon,
    )

    result = execute_conversation_action(
        db=db,
        user_id=123,
        request_id=REQUEST_ID,
        source_message_id=(
            "bbbbbbbb-2222-3333-4444-555555555555"
        ),
        action={
            "name": "sermon.delete",
            "arguments": {},
        },
        sermon_id=None,
        sermon_data=None,
        bound_sermon_id=None,
        pending_action=None,
    )

    delete_sermon.assert_not_called()
    db.delete.assert_not_called()
    db.commit.assert_not_called()

    assert result == {
        "name": "sermon.delete",
        "status": "completed",
        "result": {
            "sermon_id": 42,
        },
    }


def test_sermon_delete_commit_failure_rolls_back_transaction(
    monkeypatch,
):
    db = MagicMock()

    query = db.query.return_value
    query.filter.return_value = query

    # No prior completed execution exists, and after rollback
    # no winning concurrent execution can be recovered.
    query.first.return_value = None

    pending = _pending_sermon_delete()

    delete_sermon = MagicMock(
        return_value=SimpleNamespace(id=42)
    )

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_delete_for_user",
        delete_sermon,
    )

    db.commit.side_effect = IntegrityError(
        statement="DELETE",
        params={},
        orig=Exception(
            "database commit failed"
        ),
    )

    with pytest.raises(IntegrityError):
        execute_conversation_action(
            db=db,
            user_id=123,
            request_id=REQUEST_ID,
            source_message_id=(
                "aaaaaaaa-2222-3333-4444-555555555555"
            ),
            action={
                "name": "sermon.delete",
                "arguments": {},
            },
            sermon_id=999,
            sermon_data=None,
            bound_sermon_id=42,
            pending_action=pending,
        )

    delete_sermon.assert_called_once_with(
        db=db,
        user_id=123,
        sermon_id=42,
    )

    # The pending confirmation is scheduled for deletion in
    # the same transaction as the sermon mutation.
    db.delete.assert_called_once_with(
        pending
    )

    db.commit.assert_called_once()
    db.rollback.assert_called_once()
