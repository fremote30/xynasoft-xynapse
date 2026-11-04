from __future__ import annotations

import pytest
from pydantic import ValidationError

from xynassist_service.xyniva.structured_output import (
    XynivaStructuredOutput,
)


def test_plain_response_is_valid():
    output = XynivaStructuredOutput.model_validate(
        {
            "kind": "response",
            "content": "Grace and peace.",
        }
    )

    assert output.kind == "response"
    assert output.content == "Grace and peace."
    assert output.action is None
    assert output.confirmation is None
    assert output.prompt is None


def test_memory_remember_proposal_is_valid():
    output = XynivaStructuredOutput.model_validate(
        {
            "kind": "action",
            "content": "I can remember that.",
            "action": {
                "name": "memory.remember",
                "arguments": {
                    "memory_type": "preference",
                    "key": "sermon_tone",
                    "value": "pastoral",
                },
            },
        }
    )

    assert output.kind == "action"
    assert output.action is not None
    assert output.action.name == "memory.remember"
    assert output.action.arguments == {
        "memory_type": "preference",
        "key": "sermon_tone",
        "value": "pastoral",
    }
    assert output.prompt is None


def test_memory_forget_proposal_requires_prompt():
    with pytest.raises(
        ValidationError,
        match="confirmation prompt",
    ):
        XynivaStructuredOutput.model_validate(
            {
                "kind": "action",
                "action": {
                    "name": "memory.forget",
                    "arguments": {
                        "memory_type": "preference",
                        "key": "sermon_tone",
                    },
                },
            }
        )


def test_memory_forget_proposal_is_valid_with_prompt():
    output = XynivaStructuredOutput.model_validate(
        {
            "kind": "action",
            "content": (
                "I can forget that preference."
            ),
            "action": {
                "name": "memory.forget",
                "arguments": {
                    "memory_type": "preference",
                    "key": "sermon_tone",
                },
            },
            "prompt": (
                "Would you like me to forget that "
                "sermon-tone preference?"
            ),
        }
    )

    assert output.action is not None
    assert output.action.name == "memory.forget"
    assert output.prompt is not None


def test_memory_forget_confirmation_has_no_target():
    output = XynivaStructuredOutput.model_validate(
        {
            "kind": "confirmation",
            "content": "I'll forget it.",
            "confirmation": {
                "action_name": "memory.forget",
            },
        }
    )

    assert output.kind == "confirmation"
    assert output.action is None
    assert output.confirmation is not None
    assert (
        output.confirmation.action_name
        == "memory.forget"
    )


@pytest.mark.parametrize(
    "extra_field",
    [
        {
            "memory_type": "preference",
        },
        {
            "key": "sermon_tone",
        },
        {
            "action_request_id": (
                "12121212-3434-5656-7878-909090909090"
            ),
        },
        {
            "trusted_confirmed": True,
        },
    ],
)
def test_confirmation_rejects_server_owned_state(
    extra_field,
):
    confirmation = {
        "action_name": "memory.forget",
        **extra_field,
    }

    with pytest.raises(ValidationError):
        XynivaStructuredOutput.model_validate(
            {
                "kind": "confirmation",
                "confirmation": confirmation,
            }
        )


def test_confirmation_rejects_nonconfirmable_action():
    with pytest.raises(
        ValidationError,
        match="confirmable",
    ):
        XynivaStructuredOutput.model_validate(
            {
                "kind": "confirmation",
                "confirmation": {
                    "action_name": "memory.remember",
                },
            }
        )


def test_unknown_action_fails_closed():
    with pytest.raises(ValidationError):
        XynivaStructuredOutput.model_validate(
            {
                "kind": "action",
                "action": {
                    "name": "memory.publish",
                    "arguments": {},
                },
            }
        )


def test_model_driven_sermon_action_not_enabled_yet():
    with pytest.raises(
        ValidationError,
        match="not enabled",
    ):
        XynivaStructuredOutput.model_validate(
            {
                "kind": "action",
                "action": {
                    "name": "sermon.delete",
                    "arguments": {},
                },
                "prompt": "Delete the sermon?",
            }
        )


def test_remember_rejects_extra_confirmation_argument():
    with pytest.raises(ValidationError):
        XynivaStructuredOutput.model_validate(
            {
                "kind": "action",
                "action": {
                    "name": "memory.remember",
                    "arguments": {
                        "memory_type": "preference",
                        "key": "sermon_tone",
                        "value": "pastoral",
                        "confirmed": True,
                    },
                },
            }
        )


def test_confirmation_cannot_also_propose_action():
    with pytest.raises(
        ValidationError,
        match="Invalid confirmation output",
    ):
        XynivaStructuredOutput.model_validate(
            {
                "kind": "confirmation",
                "action": {
                    "name": "memory.forget",
                    "arguments": {
                        "memory_type": "preference",
                        "key": "sermon_tone",
                    },
                },
                "confirmation": {
                    "action_name": "memory.forget",
                },
            }
        )
