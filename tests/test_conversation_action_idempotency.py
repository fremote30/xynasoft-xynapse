from types import SimpleNamespace
from unittest.mock import MagicMock

from sqlalchemy.exc import IntegrityError

from api.models.conversation_action_execution import (
    ConversationActionExecution,
)
from api.services.conversation_actions import (
    execute_conversation_action,
)


SOURCE_MESSAGE_ID = (
    "aaaaaaaa-2222-3333-4444-555555555555"
)


REQUEST_ID = (
    "11111111-2222-4333-8444-555555555555"
)

def _action():
    return {
        "name": "sermon.save",
        "arguments": {},
    }


def test_completed_action_is_replayed_without_new_sermon(
    monkeypatch,
):
    db = MagicMock()

    existing = SimpleNamespace(
        action_name="sermon.save",
        status="completed",
        result={
            "sermon_id": 42,
        },
    )

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = existing

    build = MagicMock()

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_for_user",
        build,
    )

    result = execute_conversation_action(
        db=db,
        user_id=123,
        request_id=REQUEST_ID,
        source_message_id=SOURCE_MESSAGE_ID,
        action=_action(),
        sermon_id=None,
        sermon_data={
            "title": "Trust the Lord",
        },
    )

    assert result == {
        "name": "sermon.save",
        "status": "completed",
        "result": {
            "sermon_id": 42,
        },
    }

    build.assert_not_called()
    db.commit.assert_not_called()


def test_new_action_commits_sermon_and_execution_together(
    monkeypatch,
):
    db = MagicMock()

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    sermon = SimpleNamespace(
        id=42,
    )

    build = MagicMock(
        return_value=sermon
    )

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_for_user",
        build,
    )

    result = execute_conversation_action(
        db=db,
        user_id=123,
        request_id=REQUEST_ID,
        source_message_id=SOURCE_MESSAGE_ID,
        action=_action(),
        sermon_id=None,
        sermon_data={
            "title": "Trust the Lord",
        },
    )

    build.assert_called_once_with(
        db=db,
        user_id=123,
        payload={
            "title": "Trust the Lord",
        },
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
    assert execution.user_id == 123
    assert execution.request_id == REQUEST_ID
    assert (
        execution.source_message_id
        == SOURCE_MESSAGE_ID
    )
    assert execution.action_name == "sermon.save"
    assert execution.status == "completed"
    assert execution.result == {
        "sermon_id": 42,
    }

    db.commit.assert_called_once()

    assert result == {
        "name": "sermon.save",
        "status": "completed",
        "result": {
            "sermon_id": 42,
        },
    }


def test_unique_race_rolls_back_and_returns_winner(
    monkeypatch,
):
    db = MagicMock()

    winner = SimpleNamespace(
        action_name="sermon.save",
        status="completed",
        result={
            "sermon_id": 77,
        },
    )

    query = db.query.return_value
    query.filter.return_value = query
    query.first.side_effect = [
        None,
        winner,
    ]

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_for_user",
        MagicMock(
            return_value=SimpleNamespace(
                id=42,
            )
        ),
    )

    db.commit.side_effect = IntegrityError(
        statement="INSERT",
        params={},
        orig=Exception(
            "duplicate key"
        ),
    )

    result = execute_conversation_action(
        db=db,
        user_id=123,
        request_id=REQUEST_ID,
        source_message_id=SOURCE_MESSAGE_ID,
        action=_action(),
        sermon_id=None,
        sermon_data={
            "title": "Trust the Lord",
        },
    )

    db.rollback.assert_called_once()

    assert result == {
        "name": "sermon.save",
        "status": "completed",
        "result": {
            "sermon_id": 77,
        },
    }


def test_idempotency_is_scoped_to_authenticated_user():
    db = MagicMock()

    query = db.query.return_value
    query.filter.return_value = query

    existing = SimpleNamespace(
        action_name="sermon.save",
        status="completed",
        result={
            "sermon_id": 42,
        },
    )

    query.first.return_value = existing

    execute_conversation_action(
        db=db,
        user_id=123,
        request_id=REQUEST_ID,
        source_message_id=SOURCE_MESSAGE_ID,
        action=_action(),
        sermon_id=None,
        sermon_data={
            "title": "Trust the Lord",
        },
    )

    # SQLAlchemy expressions are evaluated inside the
    # service; this test verifies that two ownership filters
    # were applied before first().
    assert query.filter.call_count == 2


def test_idempotency_constraint_uses_request_id():
    unique_constraints = [
        constraint
        for constraint
        in ConversationActionExecution.__table__.constraints
        if constraint.__class__.__name__
        == "UniqueConstraint"
    ]

    assert len(unique_constraints) == 1

    columns = {
        column.name
        for column
        in unique_constraints[0].columns
    }

    assert columns == {
        "user_id",
        "request_id",
    }

    assert "source_message_id" not in columns


def test_same_request_replays_with_different_source_message(
    monkeypatch,
):
    db = MagicMock()

    existing = SimpleNamespace(
        action_name="sermon.save",
        status="completed",
        result={
            "sermon_id": 42,
        },
    )

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = existing

    build = MagicMock()

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_for_user",
        build,
    )

    result = execute_conversation_action(
        db=db,
        user_id=123,
        request_id=REQUEST_ID,
        source_message_id=(
            "bbbbbbbb-2222-3333-4444-555555555555"
        ),
        action=_action(),
        sermon_id=None,
        sermon_data={
            "title": "Trust the Lord",
        },
    )

    assert result == {
        "name": "sermon.save",
        "status": "completed",
        "result": {
            "sermon_id": 42,
        },
    }

    build.assert_not_called()
    db.commit.assert_not_called()


def test_different_request_ids_can_create_distinct_actions(
    monkeypatch,
):
    db = MagicMock()

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    sermons = [
        SimpleNamespace(id=42),
        SimpleNamespace(id=43),
    ]

    build = MagicMock(
        side_effect=sermons
    )

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_for_user",
        build,
    )

    second_request_id = (
        "66666666-7777-4888-8999-aaaaaaaaaaaa"
    )

    first = execute_conversation_action(
        db=db,
        user_id=123,
        request_id=REQUEST_ID,
        source_message_id=SOURCE_MESSAGE_ID,
        action=_action(),
        sermon_id=None,
        sermon_data={
            "title": "First Sermon",
        },
    )

    second = execute_conversation_action(
        db=db,
        user_id=123,
        request_id=second_request_id,
        source_message_id=SOURCE_MESSAGE_ID,
        action=_action(),
        sermon_id=None,
        sermon_data={
            "title": "Second Sermon",
        },
    )

    executions = [
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(
            call.args[0],
            ConversationActionExecution,
        )
    ]

    assert len(executions) == 2

    assert executions[0].request_id == REQUEST_ID
    assert (
        executions[1].request_id
        == second_request_id
    )

    # The same XynAssist provenance identifier must not
    # collapse two genuinely different XynaFaith requests.
    assert (
        executions[0].source_message_id
        == SOURCE_MESSAGE_ID
    )
    assert (
        executions[1].source_message_id
        == SOURCE_MESSAGE_ID
    )

    assert first["result"]["sermon_id"] == 42
    assert second["result"]["sermon_id"] == 43

    assert db.commit.call_count == 2


def test_same_request_id_is_independent_between_users(
    monkeypatch,
):
    db = MagicMock()

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    build = MagicMock(
        side_effect=[
            SimpleNamespace(id=42),
            SimpleNamespace(id=77),
        ]
    )

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_sermon_for_user",
        build,
    )

    execute_conversation_action(
        db=db,
        user_id=123,
        request_id=REQUEST_ID,
        source_message_id=SOURCE_MESSAGE_ID,
        action=_action(),
        sermon_id=None,
        sermon_data={
            "title": "User 123 Sermon",
        },
    )

    execute_conversation_action(
        db=db,
        user_id=456,
        request_id=REQUEST_ID,
        source_message_id=SOURCE_MESSAGE_ID,
        action=_action(),
        sermon_id=None,
        sermon_data={
            "title": "User 456 Sermon",
        },
    )

    executions = [
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(
            call.args[0],
            ConversationActionExecution,
        )
    ]

    assert len(executions) == 2

    assert executions[0].user_id == 123
    assert executions[1].user_id == 456

    assert executions[0].request_id == REQUEST_ID
    assert executions[1].request_id == REQUEST_ID

    assert db.commit.call_count == 2
