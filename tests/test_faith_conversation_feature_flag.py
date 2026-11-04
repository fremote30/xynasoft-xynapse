from unittest.mock import Mock

import pytest
from fastapi import HTTPException

import api.routes.faith_conversations as route


def test_xynassist_gate_allows_enabled(monkeypatch):
    monkeypatch.setattr(
        route,
        "XYNASSIST_ENABLED",
        True,
    )

    route.require_xynassist_enabled()


def test_xynassist_gate_rejects_disabled(monkeypatch):
    monkeypatch.setattr(
        route,
        "XYNASSIST_ENABLED",
        False,
    )

    with pytest.raises(HTTPException) as exc_info:
        route.require_xynassist_enabled()

    assert exc_info.value.status_code == 503
    assert (
        exc_info.value.detail
        == "Conversation service is temporarily unavailable"
    )


@pytest.mark.anyio
async def test_disabled_turn_does_not_reserve_usage(
    monkeypatch,
):
    monkeypatch.setattr(
        route,
        "XYNASSIST_ENABLED",
        False,
    )

    reserve = Mock()
    monkeypatch.setattr(
        route,
        "reserve_conversation_turn",
        reserve,
    )

    payload = route.ConversationTurnCreate(
        content="Help me prepare a sermon.",
        request_id="11111111-1111-1111-1111-111111111111",
    )

    user = Mock()
    user.id = 42

    with pytest.raises(HTTPException) as exc_info:
        await route.execute_conversation_turn(
            conversation_id="conversation-1",
            payload=payload,
            db=Mock(),
            current_user=user,
        )

    assert exc_info.value.status_code == 503
    reserve.assert_not_called()
