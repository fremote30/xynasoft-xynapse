"""Security and execution tests for Xyniva event draft actions."""

import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from api.services.church_event_service import (
    ChurchEventActionError,
    build_event_draft_for_user,
)
from api.services.conversation_actions import (
    ConversationActionContextError,
    execute_conversation_action,
)
from xynassist_service.xyniva.structured_output import (
    XynivaStructuredOutput,
)


REQUEST_ID = "22222222-2222-4333-8444-555555555555"
SOURCE_MESSAGE_ID = "bbbbbbbb-2222-3333-4444-555555555555"


def event_action(**overrides):
    arguments = {
        "title": "Friday Prayer Night",
        "description": "Join us for prayer and worship.",
        "starts_at": "2026-10-02T19:00:00",
        "ends_at": "2026-10-02T21:00:00",
        "location": "Main Sanctuary",
        "event_url": "https://example.com/friday-prayer",
    }
    arguments.update(overrides)

    return {
        "name": "event.save_draft",
        "arguments": arguments,
    }


def authenticated_user(user_id=123):
    return SimpleNamespace(
        id=user_id,
        role="pastor",
    )


def test_structured_output_accepts_event_draft():
    output = XynivaStructuredOutput.model_validate(
        {
            "kind": "action",
            "content": "I can save that event as a draft.",
            "action": event_action(),
        }
    )

    assert output.action is not None
    assert output.action.name == "event.save_draft"
    assert output.action.arguments["title"] == "Friday Prayer Night"
    assert (
        output.action.arguments["starts_at"]
        == "2026-10-02T19:00:00"
    )


@pytest.mark.parametrize(
    "extra",
    [
        {"status": "published"},
        {"church_id": 999},
        {"user_id": 999},
        {"published_at": "2026-10-02T12:00:00"},
    ],
)
def test_structured_output_rejects_authority_arguments(extra):
    arguments = {
        **event_action()["arguments"],
        **extra,
    }

    with pytest.raises(ValidationError):
        XynivaStructuredOutput.model_validate(
            {
                "kind": "action",
                "content": "Saving.",
                "action": {
                    "name": "event.save_draft",
                    "arguments": arguments,
                },
            }
        )


def test_structured_output_rejects_invalid_event_url():
    with pytest.raises(ValidationError):
        XynivaStructuredOutput.model_validate(
            {
                "kind": "action",
                "content": "Saving.",
                "action": event_action(
                    event_url="not-a-url",
                ),
            }
        )


def test_executor_uses_authenticated_user_and_trusted_church(
    monkeypatch,
):
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    user = authenticated_user()

    build = MagicMock(
        return_value=SimpleNamespace(
            id=88,
            church_id=7,
            status="draft",
        )
    )

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_event_draft_for_user",
        build,
    )

    action = event_action()

    result = execute_conversation_action(
        db=db,
        user_id=user.id,
        request_id=REQUEST_ID,
        source_message_id=SOURCE_MESSAGE_ID,
        action=action,
        sermon_id=None,
        sermon_data=None,
        current_user=user,
        church_id=7,
    )

    build.assert_called_once_with(
        db=db,
        user=user,
        church_id=7,
        event_data=action["arguments"],
    )

    assert result == {
        "name": "event.save_draft",
        "status": "completed",
        "result": {
            "event_id": 88,
            "church_id": 7,
            "status": "draft",
        },
    }

    db.commit.assert_called_once()


@pytest.mark.parametrize(
    "church_id",
    [None, 0, -1, True],
)
def test_executor_requires_trusted_church_context(
    monkeypatch,
    church_id,
):
    build = MagicMock()

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_event_draft_for_user",
        build,
    )

    user = authenticated_user()

    with pytest.raises(
        ConversationActionContextError,
        match="Trusted Church Space context",
    ):
        execute_conversation_action(
            db=MagicMock(),
            user_id=user.id,
            request_id=REQUEST_ID,
            source_message_id=SOURCE_MESSAGE_ID,
            action=event_action(),
            sermon_id=None,
            sermon_data=None,
            current_user=user,
            church_id=church_id,
        )

    build.assert_not_called()


def test_executor_rejects_mismatched_authenticated_user(
    monkeypatch,
):
    build = MagicMock()

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_event_draft_for_user",
        build,
    )

    with pytest.raises(
        ConversationActionContextError,
        match="Authenticated user context",
    ):
        execute_conversation_action(
            db=MagicMock(),
            user_id=123,
            request_id=REQUEST_ID,
            source_message_id=SOURCE_MESSAGE_ID,
            action=event_action(),
            sermon_id=None,
            sermon_data=None,
            current_user=authenticated_user(999),
            church_id=7,
        )

    build.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "published"),
        ("church_id", 999),
        ("user_id", 999),
        ("published_at", "2026-10-02T12:00:00"),
    ],
)
def test_executor_rejects_authority_arguments(
    field,
    value,
):
    user = authenticated_user()

    action = event_action()
    action["arguments"][field] = value

    with pytest.raises(
        ConversationActionContextError,
        match="accepts only event content fields",
    ):
        execute_conversation_action(
            db=MagicMock(),
            user_id=user.id,
            request_id=REQUEST_ID,
            source_message_id=SOURCE_MESSAGE_ID,
            action=action,
            sermon_id=None,
            sermon_data=None,
            current_user=user,
            church_id=7,
        )


@pytest.mark.parametrize(
    ("error", "message"),
    [
        (
            ChurchEventActionError(
                "Church Space not found"
            ),
            "Church Space not found",
        ),
        (
            ChurchEventActionError(
                "Church membership is not active"
            ),
            "Church membership is not active",
        ),
        (
            ChurchEventActionError(
                "Insufficient Church Space permission"
            ),
            "Insufficient Church Space permission",
        ),
        (
            ChurchEventActionError(
                "Church events are not available"
            ),
            "Church events are not available",
        ),
    ],
)
def test_executor_fails_closed_on_product_authorization(
    monkeypatch,
    error,
    message,
):
    db = MagicMock()
    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_event_draft_for_user",
        MagicMock(side_effect=error),
    )

    user = authenticated_user()

    with pytest.raises(
        ConversationActionContextError,
        match=message,
    ):
        execute_conversation_action(
            db=db,
            user_id=user.id,
            request_id=REQUEST_ID,
            source_message_id=SOURCE_MESSAGE_ID,
            action=event_action(),
            sermon_id=None,
            sermon_data=None,
            current_user=user,
            church_id=7,
        )

    db.commit.assert_not_called()


def test_completed_event_action_replays_without_mutation(
    monkeypatch,
):
    db = MagicMock()

    existing = SimpleNamespace(
        action_name="event.save_draft",
        status="completed",
        result={
            "event_id": 88,
            "church_id": 7,
            "status": "draft",
        },
    )

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = existing

    build = MagicMock()

    monkeypatch.setattr(
        "api.services.conversation_actions."
        "build_event_draft_for_user",
        build,
    )

    user = authenticated_user()

    result = execute_conversation_action(
        db=db,
        user_id=user.id,
        request_id=REQUEST_ID,
        source_message_id=SOURCE_MESSAGE_ID,
        action=event_action(),
        sermon_id=None,
        sermon_data=None,
        current_user=user,
        church_id=7,
    )

    assert result == {
        "name": "event.save_draft",
        "status": "completed",
        "result": {
            "event_id": 88,
            "church_id": 7,
            "status": "draft",
        },
    }

    build.assert_not_called()
    db.commit.assert_not_called()


def test_replay_cannot_be_rebound_to_another_action():
    db = MagicMock()

    existing = SimpleNamespace(
        action_name="announcement.save_draft",
        status="completed",
        result={
            "announcement_id": 55,
            "church_id": 7,
            "status": "draft",
        },
    )

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = existing

    user = authenticated_user()

    with pytest.raises(
        ConversationActionContextError,
        match="idempotency conflict",
    ):
        execute_conversation_action(
            db=db,
            user_id=user.id,
            request_id=REQUEST_ID,
            source_message_id=SOURCE_MESSAGE_ID,
            action=event_action(),
            sermon_id=None,
            sermon_data=None,
            current_user=user,
            church_id=7,
        )


def test_replayed_event_returns_original_church():
    db = MagicMock()

    existing = SimpleNamespace(
        action_name="event.save_draft",
        status="completed",
        result={
            "event_id": 88,
            "church_id": 7,
            "status": "draft",
        },
    )

    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = existing

    user = authenticated_user()

    result = execute_conversation_action(
        db=db,
        user_id=user.id,
        request_id=REQUEST_ID,
        source_message_id=SOURCE_MESSAGE_ID,
        action=event_action(),
        sermon_id=None,
        sermon_data=None,
        current_user=user,
        # Replay cannot mutate/rebind original result.
        church_id=999,
    )

    assert result["result"]["church_id"] == 7
    assert result["result"]["event_id"] == 88
    db.commit.assert_not_called()


def test_authoritative_service_forces_draft(
    monkeypatch,
):
    db = MagicMock()
    user = authenticated_user()

    monkeypatch.setattr(
        "api.services.church_event_service."
        "require_church_permission",
        MagicMock(),
    )

    monkeypatch.setattr(
        "api.services.church_event_service."
        "has_entitlement",
        lambda db, user, entitlement_key, church_id=None: True,
    )

    event = build_event_draft_for_user(
        db=db,
        user=user,
        church_id=7,
        event_data={
            "title": "  Friday Prayer Night  ",
            "description": "  Prayer and worship.  ",
            "starts_at": "2026-10-02T19:00:00",
            "ends_at": "2026-10-02T21:00:00",
            "location": "  Main Sanctuary  ",
            "event_url": "https://example.com/prayer",
            # Direct service caller still cannot publish.
            "status": "published",
        },
    )

    assert event.church_id == 7
    assert event.created_by_user_id == user.id
    assert event.title == "Friday Prayer Night"
    assert event.description == "Prayer and worship."
    assert event.location == "Main Sanctuary"
    assert event.status == "draft"
    assert event.published_at is None


def test_authoritative_service_rejects_end_before_start(
    monkeypatch,
):
    db = MagicMock()
    user = authenticated_user()

    monkeypatch.setattr(
        "api.services.church_event_service."
        "require_church_permission",
        MagicMock(),
    )

    monkeypatch.setattr(
        "api.services.church_event_service."
        "has_entitlement",
        lambda db, user, entitlement_key, church_id=None: True,
    )

    with pytest.raises(
        ChurchEventActionError,
        match="end cannot precede start",
    ):
        build_event_draft_for_user(
            db=db,
            user=user,
            church_id=7,
            event_data={
                "title": "Impossible Event",
                "starts_at": "2026-10-02T21:00:00",
                "ends_at": "2026-10-02T19:00:00",
            },
        )


def test_authoritative_service_checks_permission_and_entitlement(
    monkeypatch,
):
    db = MagicMock()
    user = authenticated_user()

    permission = MagicMock()

    monkeypatch.setattr(
        "api.services.church_event_service."
        "require_church_permission",
        permission,
    )

    entitlement = MagicMock(return_value=True)

    monkeypatch.setattr(
        "api.services.church_event_service."
        "has_entitlement",
        entitlement,
    )

    build_event_draft_for_user(
        db=db,
        user=user,
        church_id=7,
        event_data={
            "title": "Friday Prayer Night",
            "starts_at": "2026-10-02T19:00:00",
        },
    )

    permission.assert_called_once()
    kwargs = permission.call_args.kwargs
    assert kwargs["church_id"] == 7
    assert kwargs["user_id"] == user.id

    entitlement.assert_called_once()
    assert entitlement.call_args.kwargs["church_id"] == 7
