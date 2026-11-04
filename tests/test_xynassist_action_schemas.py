import pytest
from pydantic import ValidationError

from xynassist_service.schemas.conversations import (
    ConversationAction,
)


def test_conversation_action_accepts_allowlisted_action():
    action = ConversationAction(
        name="sermon.save",
        arguments={},
    )

    assert action.name == "sermon.save"
    assert action.arguments == {}


@pytest.mark.parametrize(
    "name",
    [
        "sermon.save",
        "sermon.update",
        "sermon.delete",
    ],
)
def test_conversation_action_accepts_current_actions(
    name,
):
    action = ConversationAction(
        name=name,
    )

    assert action.name == name
    assert action.arguments == {}


def test_conversation_action_rejects_unknown_action():
    with pytest.raises(ValidationError):
        ConversationAction(
            name="sermon.publish",
        )


def test_conversation_action_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ConversationAction(
            name="sermon.save",
            user_id=999,
        )


def test_conversation_action_default_arguments_are_independent():
    first = ConversationAction(
        name="sermon.save",
    )
    second = ConversationAction(
        name="sermon.save",
    )

    first.arguments["unexpected"] = True

    assert second.arguments == {}


def test_memory_remember_accepts_typed_arguments():
    action = ConversationAction(
        name="memory.remember",
        arguments={
            "memory_type": "preference",
            "key": "sermon_length",
            "value": "20 minutes",
        },
    )

    assert action.arguments == {
        "memory_type": "preference",
        "key": "sermon_length",
        "value": "20 minutes",
    }


def test_memory_forget_accepts_typed_arguments():
    action = ConversationAction(
        name="memory.forget",
        arguments={
            "memory_type": "preference",
            "key": "sermon_length",
        },
    )

    assert action.arguments == {
        "memory_type": "preference",
        "key": "sermon_length",
    }


@pytest.mark.parametrize(
    "arguments",
    [
        {
            "memory_type": "sensitive",
            "key": "private_note",
            "value": "secret",
        },
        {
            "memory_type": "preference",
            "key": "",
            "value": "20 minutes",
        },
        {
            "memory_type": "preference",
            "key": "sermon_length",
            "value": "",
        },
        {
            "memory_type": "preference",
            "key": "sermon_length",
            "value": "20 minutes",
            "external_user_id": "attacker",
        },
    ],
)
def test_memory_remember_rejects_invalid_arguments(
    arguments,
):
    with pytest.raises(ValidationError):
        ConversationAction(
            name="memory.remember",
            arguments=arguments,
        )


@pytest.mark.parametrize(
    "arguments",
    [
        {
            "memory_type": "sensitive",
            "key": "private_note",
        },
        {
            "memory_type": "preference",
            "key": "",
        },
        {
            "memory_type": "preference",
            "key": "sermon_length",
            "memory_id": "attacker-controlled",
        },
    ],
)
def test_memory_forget_rejects_invalid_arguments(
    arguments,
):
    with pytest.raises(ValidationError):
        ConversationAction(
            name="memory.forget",
            arguments=arguments,
        )


def test_sermon_actions_still_reject_arguments():
    with pytest.raises(ValidationError):
        ConversationAction(
            name="sermon.save",
            arguments={
                "memory_type": "preference",
            },
        )
