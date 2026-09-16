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
