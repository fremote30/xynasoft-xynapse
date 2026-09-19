import json

import pytest

from xynassist_service.xyniva.structured_output import (
    XynivaStructuredOutputError,
    parse_xyniva_structured_output,
)


def _parse(payload):
    return parse_xyniva_structured_output(
        json.dumps(payload)
    )


def test_parser_accepts_response():
    result = _parse(
        {
            "kind": "response",
            "content": "Grace and peace.",
        }
    )

    assert result.kind == "response"
    assert result.content == "Grace and peace."


def test_parser_accepts_confirmation():
    result = _parse(
        {
            "kind": "confirmation",
            "confirmation": {
                "action_name": "memory.forget",
            },
        }
    )

    assert result.confirmation is not None
    assert (
        result.confirmation.action_name
        == "memory.forget"
    )
    assert result.action is None


def test_parser_rejects_malformed_json():
    with pytest.raises(
        XynivaStructuredOutputError,
    ):
        parse_xyniva_structured_output(
            "not-json"
        )


def test_parser_rejects_non_object():
    with pytest.raises(
        XynivaStructuredOutputError,
        match="JSON object",
    ):
        parse_xyniva_structured_output(
            "[]"
        )


def test_parser_rejects_markdown_fence():
    with pytest.raises(
        XynivaStructuredOutputError,
        match="valid JSON",
    ):
        parse_xyniva_structured_output(
            '```json\n'
            '{"kind":"response","content":"Hello"}'
            '\n```'
        )


def test_parser_rejects_server_state():
    with pytest.raises(
        XynivaStructuredOutputError,
        match="failed validation",
    ):
        _parse(
            {
                "kind": "confirmation",
                "confirmation": {
                    "action_name": "memory.forget",
                    "trusted_confirmed": True,
                },
            }
        )


def test_parser_rejects_action_request_id():
    with pytest.raises(
        XynivaStructuredOutputError,
        match="failed validation",
    ):
        _parse(
            {
                "kind": "confirmation",
                "confirmation": {
                    "action_name": "memory.forget",
                    "action_request_id": "model-owned-id",
                },
            }
        )


def test_parser_rejects_remember_confirmation():
    with pytest.raises(
        XynivaStructuredOutputError,
        match="failed validation",
    ):
        _parse(
            {
                "kind": "confirmation",
                "confirmation": {
                    "action_name": "memory.remember",
                },
            }
        )


def test_parser_rejects_unknown_action():
    with pytest.raises(
        XynivaStructuredOutputError,
        match="failed validation",
    ):
        _parse(
            {
                "kind": "action",
                "action": {
                    "name": "memory.publish",
                    "arguments": {},
                },
            }
        )


def test_parser_rejects_confirmed_argument():
    with pytest.raises(
        XynivaStructuredOutputError,
        match="failed validation",
    ):
        _parse(
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
