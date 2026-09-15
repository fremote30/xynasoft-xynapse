from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest
from fastapi import HTTPException

import api.routes.faith_conversations as conversations
from api.services.ai_usage_metering import UsageLimitExceeded
from api.services.xynassist_client import XynAssistUnavailableError
from api.services.xyniva_usage_service import XynivaUsageDenied


CONVERSATION_ID = "conversation-v2-metering"
REQUEST_ID = UUID(
    "11111111-2222-3333-4444-555555555555"
)


@pytest.fixture(autouse=True)
def enable_xynassist_for_metering_tests(
    monkeypatch,
):
    """
    These tests exercise metering around an enabled XynAssist
    conversation boundary. Feature-flag fail-closed behavior is
    tested separately.
    """
    monkeypatch.setattr(
        conversations,
        "XYNASSIST_ENABLED",
        True,
    )


def _payload(
    *,
    content: str = "Help me understand Romans 8.",
):
    return conversations.ConversationTurnCreate(
        content=content,
        request_id=REQUEST_ID,
    )


def _user():
    return SimpleNamespace(
        id=7,
        role="member",
    )


@pytest.mark.anyio
async def test_turn_reserves_before_xynassist_and_consumes_after_success(
    monkeypatch,
):
    db = Mock()
    order = []

    def reserve(*args, **kwargs):
        order.append("reserve")

        assert kwargs["user"].id == 7
        assert kwargs["request_id"] == str(REQUEST_ID)

    def consume(*args, **kwargs):
        order.append("consume")

        assert kwargs["request_id"] == str(REQUEST_ID)

    def release(*args, **kwargs):
        order.append("release")

    class FakeClient:
        async def execute_conversation_turn(
            self,
            *,
            external_user_id,
            conversation_id,
            request_id,
            content,
            context,
        ):
            order.append("xynassist")

            assert external_user_id == "7"
            assert conversation_id == CONVERSATION_ID
            assert request_id == str(REQUEST_ID)
            assert content == "Help me understand Romans 8."
            assert context is None

            return {
                "assistant_message": "Test response",
            }

    monkeypatch.setattr(
        conversations,
        "reserve_conversation_turn",
        reserve,
    )
    monkeypatch.setattr(
        conversations,
        "consume_conversation_turn",
        consume,
    )
    monkeypatch.setattr(
        conversations,
        "release_conversation_turn",
        release,
    )
    monkeypatch.setattr(
        conversations,
        "XynAssistClient",
        FakeClient,
    )

    result = await conversations.execute_conversation_turn(
        conversation_id=CONVERSATION_ID,
        payload=_payload(),
        db=db,
        current_user=_user(),
    )

    assert result == {
        "assistant_message": "Test response",
    }

    assert order == [
        "reserve",
        "xynassist",
        "consume",
    ]


@pytest.mark.anyio
async def test_denied_entitlement_never_calls_xynassist(
    monkeypatch,
):
    db = Mock()
    called = False

    def reserve(*args, **kwargs):
        raise XynivaUsageDenied("not entitled")

    class FakeClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            nonlocal called
            called = True
            return {}

    monkeypatch.setattr(
        conversations,
        "reserve_conversation_turn",
        reserve,
    )
    monkeypatch.setattr(
        conversations,
        "XynAssistClient",
        FakeClient,
    )

    with pytest.raises(HTTPException) as exc_info:
        await conversations.execute_conversation_turn(
            conversation_id=CONVERSATION_ID,
            payload=_payload(),
            db=db,
            current_user=_user(),
        )

    assert exc_info.value.status_code == 403
    assert called is False


@pytest.mark.anyio
async def test_usage_cap_never_calls_xynassist(
    monkeypatch,
):
    db = Mock()
    called = False

    def reserve(*args, **kwargs):
        raise UsageLimitExceeded(
            "usage limit reached"
        )

    class FakeClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            nonlocal called
            called = True
            return {}

    monkeypatch.setattr(
        conversations,
        "reserve_conversation_turn",
        reserve,
    )
    monkeypatch.setattr(
        conversations,
        "XynAssistClient",
        FakeClient,
    )

    with pytest.raises(HTTPException) as exc_info:
        await conversations.execute_conversation_turn(
            conversation_id=CONVERSATION_ID,
            payload=_payload(),
            db=db,
            current_user=_user(),
        )

    assert exc_info.value.status_code == 429
    assert called is False


@pytest.mark.anyio
async def test_xynassist_failure_releases_reserved_usage(
    monkeypatch,
):
    db = Mock()
    order = []

    def reserve(*args, **kwargs):
        order.append("reserve")

    def consume(*args, **kwargs):
        order.append("consume")

    def release(*args, **kwargs):
        order.append("release")
        assert kwargs["request_id"] == str(REQUEST_ID)

    class FakeClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            order.append("xynassist")
            raise XynAssistUnavailableError(
                "offline"
            )

    monkeypatch.setattr(
        conversations,
        "reserve_conversation_turn",
        reserve,
    )
    monkeypatch.setattr(
        conversations,
        "consume_conversation_turn",
        consume,
    )
    monkeypatch.setattr(
        conversations,
        "release_conversation_turn",
        release,
    )
    monkeypatch.setattr(
        conversations,
        "XynAssistClient",
        FakeClient,
    )

    with pytest.raises(HTTPException) as exc_info:
        await conversations.execute_conversation_turn(
            conversation_id=CONVERSATION_ID,
            payload=_payload(),
            db=db,
            current_user=_user(),
        )

    assert exc_info.value.status_code == 503

    assert order == [
        "reserve",
        "xynassist",
        "release",
    ]


@pytest.mark.anyio
async def test_successful_ai_turn_is_not_released_if_consume_fails(
    monkeypatch,
):
    db = Mock()
    order = []

    def reserve(*args, **kwargs):
        order.append("reserve")

    def consume(*args, **kwargs):
        order.append("consume")
        raise RuntimeError(
            "database unavailable"
        )

    def release(*args, **kwargs):
        order.append("release")

    class FakeClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            order.append("xynassist")
            return {
                "assistant_message": "Generated",
            }

    monkeypatch.setattr(
        conversations,
        "reserve_conversation_turn",
        reserve,
    )
    monkeypatch.setattr(
        conversations,
        "consume_conversation_turn",
        consume,
    )
    monkeypatch.setattr(
        conversations,
        "release_conversation_turn",
        release,
    )
    monkeypatch.setattr(
        conversations,
        "XynAssistClient",
        FakeClient,
    )

    with pytest.raises(HTTPException) as exc_info:
        await conversations.execute_conversation_turn(
            conversation_id=CONVERSATION_ID,
            payload=_payload(),
            db=db,
            current_user=_user(),
        )

    assert exc_info.value.status_code == 500

    # The external AI cost has already been incurred.
    # Its durable reservation must not be returned as though
    # the AI request never happened.
    assert order == [
        "reserve",
        "xynassist",
        "consume",
    ]


@pytest.mark.anyio
async def test_plain_ai_response_consumes_exactly_once(
    monkeypatch,
):
    db = Mock()

    reservations = []
    consumptions = []
    releases = []

    def reserve(*args, **kwargs):
        reservations.append(
            kwargs["request_id"]
        )

    def consume(*args, **kwargs):
        consumptions.append(
            kwargs["request_id"]
        )

    def release(*args, **kwargs):
        releases.append(
            kwargs["request_id"]
        )

    class FakeClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            return {
                "assistant_message": "Answer",
            }

    monkeypatch.setattr(
        conversations,
        "reserve_conversation_turn",
        reserve,
    )
    monkeypatch.setattr(
        conversations,
        "consume_conversation_turn",
        consume,
    )
    monkeypatch.setattr(
        conversations,
        "release_conversation_turn",
        release,
    )
    monkeypatch.setattr(
        conversations,
        "XynAssistClient",
        FakeClient,
    )

    await conversations.execute_conversation_turn(
        conversation_id=CONVERSATION_ID,
        payload=_payload(),
        db=db,
        current_user=_user(),
    )

    expected = str(REQUEST_ID)

    assert reservations == [expected]
    assert consumptions == [expected]
    assert releases == []


@pytest.mark.anyio
async def test_xynassist_conflict_does_not_release_usage(
    monkeypatch,
):
    """
    A server-side idempotency conflict may refer to a request whose
    AI work was already completed and whose local quota is consumed.

    XynaFaith must never try to release that usage.
    """
    from api.services.xynassist_client import (
        XynAssistConflictError,
    )

    db = Mock()
    order = []

    def reserve(*args, **kwargs):
        order.append("reserve")

    def consume(*args, **kwargs):
        order.append("consume")

    def release(*args, **kwargs):
        order.append("release")

    class FakeClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            order.append("xynassist")

            assert kwargs["request_id"] == str(
                REQUEST_ID
            )

            raise XynAssistConflictError(
                "conflicting request_id"
            )

    monkeypatch.setattr(
        conversations,
        "reserve_conversation_turn",
        reserve,
    )
    monkeypatch.setattr(
        conversations,
        "consume_conversation_turn",
        consume,
    )
    monkeypatch.setattr(
        conversations,
        "release_conversation_turn",
        release,
    )
    monkeypatch.setattr(
        conversations,
        "XynAssistClient",
        FakeClient,
    )

    with pytest.raises(HTTPException) as exc_info:
        await conversations.execute_conversation_turn(
            conversation_id=CONVERSATION_ID,
            payload=_payload(
                content="Different content",
            ),
            db=db,
            current_user=_user(),
        )

    assert exc_info.value.status_code == 409

    assert order == [
        "reserve",
        "xynassist",
    ]


@pytest.mark.anyio
async def test_xynassist_unavailable_still_releases_usage(
    monkeypatch,
):
    """
    The conflict rule must not weaken ordinary failure accounting.
    A genuine pre-success infrastructure failure still releases.
    """
    db = Mock()
    order = []

    def reserve(*args, **kwargs):
        order.append("reserve")

    def release(*args, **kwargs):
        order.append("release")

    class FakeClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            order.append("xynassist")
            raise XynAssistUnavailableError(
                "offline"
            )

    monkeypatch.setattr(
        conversations,
        "reserve_conversation_turn",
        reserve,
    )
    monkeypatch.setattr(
        conversations,
        "release_conversation_turn",
        release,
    )
    monkeypatch.setattr(
        conversations,
        "XynAssistClient",
        FakeClient,
    )

    with pytest.raises(HTTPException) as exc_info:
        await conversations.execute_conversation_turn(
            conversation_id=CONVERSATION_ID,
            payload=_payload(),
            db=db,
            current_user=_user(),
        )

    assert exc_info.value.status_code == 503

    assert order == [
        "reserve",
        "xynassist",
        "release",
    ]


@pytest.mark.anyio
async def test_xynassist_in_progress_does_not_release_usage(
    monkeypatch,
):
    """
    A request already processing remotely may still complete.

    Releasing its reservation could allow the same logical AI work
    to consume capacity twice, so the reservation remains intact.
    """
    from api.services.xynassist_client import (
        XynAssistRequestInProgressError,
    )

    db = Mock()
    order = []

    def reserve(*args, **kwargs):
        order.append("reserve")

    def consume(*args, **kwargs):
        order.append("consume")

    def release(*args, **kwargs):
        order.append("release")

    class FakeClient:
        async def execute_conversation_turn(
            self,
            **kwargs,
        ):
            order.append("xynassist")

            assert kwargs["request_id"] == str(
                REQUEST_ID
            )

            raise XynAssistRequestInProgressError(
                "Turn request is already processing"
            )

    monkeypatch.setattr(
        conversations,
        "reserve_conversation_turn",
        reserve,
    )
    monkeypatch.setattr(
        conversations,
        "consume_conversation_turn",
        consume,
    )
    monkeypatch.setattr(
        conversations,
        "release_conversation_turn",
        release,
    )
    monkeypatch.setattr(
        conversations,
        "XynAssistClient",
        FakeClient,
    )

    with pytest.raises(HTTPException) as exc_info:
        await conversations.execute_conversation_turn(
            conversation_id=CONVERSATION_ID,
            payload=_payload(),
            db=db,
            current_user=_user(),
        )

    assert exc_info.value.status_code == 409
    assert (
        exc_info.value.detail
        == "This conversation request is already being processed"
    )

    assert order == [
        "reserve",
        "xynassist",
    ]
