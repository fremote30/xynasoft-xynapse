from __future__ import annotations

import httpx
import pytest

from api.services.xynassist_client import (
    XynAssistClient,
    XynAssistConfigurationError,
    XynAssistResponseError,
    XynAssistUnavailableError,
)


SERMON_PAYLOAD = {
    "input": "Trusting God during uncertainty",
    "scripture": "Proverbs 3:5-6",
    "denomination": "pentecostal",
    "audience": "general congregation",
    "context": "",
    "tone": "balanced",
    "duration": "30",
}


@pytest.fixture
def anyio_backend():
    """Run async integration-client tests on asyncio only."""
    return "asyncio"


SERMON_RESPONSE = {
    "title": "Trust in the Lord",
    "scripture": "Proverbs 3:5-6",
    "introduction": "Opening",
    "main_points": [
        {
            "title": "Trust",
            "content": "Trust God fully.",
        }
    ],
    "application": "Walk by faith.",
    "conclusion": "Trust Him.",
}


@pytest.mark.anyio
async def test_generate_sermon_posts_expected_contract():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "POST"

        assert (
            request.url.path
            == "/api/v1/integrations/xynafaith/sermons/generate"
        )

        import json

        payload = json.loads(
            request.content.decode("utf-8")
        )

        assert payload == SERMON_PAYLOAD

        return httpx.Response(
            200,
            json=SERMON_RESPONSE,
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    result = await client.generate_sermon(
        SERMON_PAYLOAD
    )

    assert result == SERMON_RESPONSE


@pytest.mark.anyio
async def test_generate_sermon_rejects_error_response():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            503,
            json={"detail": "Unavailable"},
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistResponseError,
        match="HTTP 503",
    ):
        await client.generate_sermon(
            SERMON_PAYLOAD
        )


@pytest.mark.anyio
async def test_generate_sermon_rejects_invalid_json():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"not-json",
            headers={
                "content-type": "text/plain",
            },
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistResponseError,
        match="invalid JSON",
    ):
        await client.generate_sermon(
            SERMON_PAYLOAD
        )


@pytest.mark.anyio
async def test_generate_sermon_rejects_non_object_json():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json=["unexpected"],
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistResponseError,
        match="invalid response shape",
    ):
        await client.generate_sermon(
            SERMON_PAYLOAD
        )


@pytest.mark.anyio
async def test_generate_sermon_translates_network_failure():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "connection refused",
            request=request,
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistUnavailableError,
        match="Unable to reach XynAssist",
    ):
        await client.generate_sermon(
            SERMON_PAYLOAD
        )


@pytest.mark.anyio
async def test_generate_sermon_sends_service_credential():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            request.headers[
                "X-XynAssist-Service-Token"
            ]
            == "test-service-token"
        )

        return httpx.Response(
            200,
            json=SERMON_RESPONSE,
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    result = await client.generate_sermon(
        SERMON_PAYLOAD
    )

    assert result == SERMON_RESPONSE


@pytest.mark.anyio
async def test_generate_sermon_fails_closed_without_service_credential():
    from api.services.xynassist_client import (
        XynAssistConfigurationError,
    )

    called = False

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal called
        called = True

        return httpx.Response(
            200,
            json=SERMON_RESPONSE,
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistConfigurationError,
        match="not configured",
    ):
        await client.generate_sermon(
            SERMON_PAYLOAD
        )

    assert called is False


CONVERSATION_ID = (
    "11111111-2222-3333-4444-555555555555"
)

CONVERSATION_RESPONSE = {
    "id": CONVERSATION_ID,
    "product": "xynafaith",
    "title": "Sunday sermon",
    "status": "active",
    "created_at": "2026-08-31T03:00:00Z",
    "updated_at": "2026-08-31T03:00:00Z",
}

CONVERSATION_DETAIL_RESPONSE = {
    **CONVERSATION_RESPONSE,
    "messages": [],
}

TURN_RESPONSE = {
    "conversation": CONVERSATION_DETAIL_RESPONSE,
    "user_message": {
        "id": "aaaaaaaa-2222-3333-4444-555555555555",
        "conversation_id": CONVERSATION_ID,
        "role": "user",
        "content": (
            "I need a sermon on Proverbs 3."
        ),
        "skill": "sermon.generate",
        "created_at": "2026-08-31T03:01:00Z",
    },
    "assistant_message": {
        "id": "bbbbbbbb-2222-3333-4444-555555555555",
        "conversation_id": CONVERSATION_ID,
        "role": "assistant",
        "content": '{"title":"Trust the Lord"}',
        "skill": "sermon.generate",
        "created_at": "2026-08-31T03:01:01Z",
    },
    "skill": "sermon.generate",
}


@pytest.mark.anyio
async def test_create_conversation_posts_trusted_identity():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "POST"

        assert (
            request.url.path
            == "/api/v1/integrations/xynafaith/conversations"
        )

        assert (
            request.headers[
                "X-XynAssist-Service-Token"
            ]
            == "test-service-token"
        )

        assert (
            request.headers[
                "X-XynAssist-External-User-Id"
            ]
            == "123"
        )

        import json

        payload = json.loads(
            request.content.decode("utf-8")
        )

        assert payload == {
            "title": "Sunday sermon",
        }

        return httpx.Response(
            201,
            json=CONVERSATION_RESPONSE,
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    result = await client.create_conversation(
        external_user_id="123",
        title="Sunday sermon",
    )

    assert result == CONVERSATION_RESPONSE


@pytest.mark.anyio
async def test_list_conversations_gets_trusted_owner():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "GET"

        assert (
            request.url.path
            == "/api/v1/integrations/xynafaith/conversations"
        )

        assert (
            request.headers[
                "X-XynAssist-External-User-Id"
            ]
            == "123"
        )

        return httpx.Response(
            200,
            json=[CONVERSATION_RESPONSE],
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    result = await client.list_conversations(
        external_user_id="123",
    )

    assert result == [
        CONVERSATION_RESPONSE
    ]


@pytest.mark.anyio
async def test_get_conversation_uses_trusted_owner():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "GET"

        assert request.url.path == (
            "/api/v1/integrations/xynafaith/"
            f"conversations/{CONVERSATION_ID}"
        )

        assert (
            request.headers[
                "X-XynAssist-External-User-Id"
            ]
            == "123"
        )

        return httpx.Response(
            200,
            json=CONVERSATION_DETAIL_RESPONSE,
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    result = await client.get_conversation(
        external_user_id="123",
        conversation_id=CONVERSATION_ID,
    )

    assert result == (
        CONVERSATION_DETAIL_RESPONSE
    )


@pytest.mark.anyio
async def test_execute_conversation_turn_posts_content():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "POST"

        assert request.url.path == (
            "/api/v1/integrations/xynafaith/"
            f"conversations/{CONVERSATION_ID}/turns"
        )

        assert (
            request.headers[
                "X-XynAssist-Service-Token"
            ]
            == "test-service-token"
        )

        assert (
            request.headers[
                "X-XynAssist-External-User-Id"
            ]
            == "123"
        )

        import json

        payload = json.loads(
            request.content.decode("utf-8")
        )

        assert payload == {
            "content": (
                "I need a sermon on Proverbs 3."
            ),
        }

        return httpx.Response(
            200,
            json=TURN_RESPONSE,
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    result = (
        await client.execute_conversation_turn(
            external_user_id="123",
            conversation_id=CONVERSATION_ID,
            content=(
                "I need a sermon on Proverbs 3."
            ),
        )
    )

    assert result == TURN_RESPONSE


@pytest.mark.anyio
async def test_conversation_client_rejects_blank_external_user():
    called = False

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal called
        called = True

        return httpx.Response(
            200,
            json={},
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistConfigurationError,
        match="external user",
    ):
        await client.create_conversation(
            external_user_id="   ",
            title=None,
        )

    assert called is False


@pytest.mark.anyio
async def test_conversation_client_normalizes_external_user():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            request.headers[
                "X-XynAssist-External-User-Id"
            ]
            == "123"
        )

        return httpx.Response(
            201,
            json=CONVERSATION_RESPONSE,
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    result = await client.create_conversation(
        external_user_id=" 123 ",
        title="Sunday sermon",
    )

    assert result == CONVERSATION_RESPONSE


@pytest.mark.anyio
async def test_conversation_request_fails_closed_without_service_credential():
    called = False

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        nonlocal called
        called = True

        return httpx.Response(
            200,
            json=CONVERSATION_RESPONSE,
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistConfigurationError,
        match="not configured",
    ):
        await client.create_conversation(
            external_user_id="123",
            title="Sunday sermon",
        )

    assert called is False


@pytest.mark.anyio
async def test_create_conversation_rejects_non_object_response():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            201,
            json=[CONVERSATION_RESPONSE],
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistResponseError,
        match="invalid response shape",
    ):
        await client.create_conversation(
            external_user_id="123",
            title="Sunday sermon",
        )


@pytest.mark.anyio
async def test_list_conversations_rejects_non_list_response():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json=CONVERSATION_RESPONSE,
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistResponseError,
        match="invalid response shape",
    ):
        await client.list_conversations(
            external_user_id="123",
        )


@pytest.mark.anyio
async def test_list_conversations_rejects_invalid_items():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json=[
                CONVERSATION_RESPONSE,
                "invalid",
            ],
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistResponseError,
        match="invalid response shape",
    ):
        await client.list_conversations(
            external_user_id="123",
        )


@pytest.mark.anyio
async def test_get_conversation_rejects_non_object_response():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json=[],
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistResponseError,
        match="invalid response shape",
    ):
        await client.get_conversation(
            external_user_id="123",
            conversation_id=CONVERSATION_ID,
        )


@pytest.mark.anyio
async def test_execute_turn_rejects_non_object_response():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            200,
            json=[],
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistResponseError,
        match="invalid response shape",
    ):
        await client.execute_conversation_turn(
            external_user_id="123",
            conversation_id=CONVERSATION_ID,
            content="Make point two stronger.",
        )


@pytest.mark.anyio
async def test_conversation_request_translates_network_failure():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        raise httpx.ConnectError(
            "connection refused",
            request=request,
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistUnavailableError,
        match="Unable to reach XynAssist",
    ):
        await client.list_conversations(
            external_user_id="123",
        )


@pytest.mark.anyio
async def test_conversation_request_rejects_upstream_error():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            404,
            json={"detail": "Not found"},
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistResponseError,
        match="HTTP 404",
    ):
        await client.get_conversation(
            external_user_id="123",
            conversation_id=CONVERSATION_ID,
        )
