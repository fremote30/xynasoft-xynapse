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


TURN_REQUEST_ID = (
    "99999999-8888-7777-6666-555555555555"
)

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
            "request_id": TURN_REQUEST_ID,
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
            request_id=TURN_REQUEST_ID,
            content=(
                "I need a sermon on Proverbs 3."
            ),
        )
    )

    assert result == TURN_RESPONSE



@pytest.mark.anyio
async def test_execute_conversation_turn_posts_context():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "POST"

        import json

        payload = json.loads(
            request.content.decode("utf-8")
        )

        assert payload == {
            "request_id": TURN_REQUEST_ID,
            "content": "Save this.",
            "context": {
                "active_resource": "sermon",
            },
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

    result = await client.execute_conversation_turn(
        external_user_id="123",
        conversation_id=CONVERSATION_ID,
        request_id=TURN_REQUEST_ID,
        content="Save this.",
        context={
            "active_resource": "sermon",
        },
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
            request_id=TURN_REQUEST_ID,
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


@pytest.mark.anyio
async def test_conversation_turn_translates_request_conflict():
    from api.services.xynassist_client import (
        XynAssistConflictError,
    )

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            409,
            json={
                "detail": "request_id conflict",
            },
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistConflictError,
        match="request_id conflict",
    ):
        await client.execute_conversation_turn(
            external_user_id="123",
            conversation_id=CONVERSATION_ID,
            request_id=TURN_REQUEST_ID,
            content="Different content",
        )


@pytest.mark.anyio
async def test_conversation_turn_translates_request_in_progress():
    from api.services.xynassist_client import (
        XynAssistRequestInProgressError,
    )

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            409,
            json={
                "detail": "Turn request is already processing",
            },
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistRequestInProgressError,
        match="already processing",
    ):
        await client.execute_conversation_turn(
            external_user_id="123",
            conversation_id=CONVERSATION_ID,
            request_id=TURN_REQUEST_ID,
            content="Retry me",
        )


@pytest.mark.anyio
async def test_conversation_turn_translates_nonreplayable_state():
    from api.services.xynassist_client import (
        XynAssistRequestStateError,
    )

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        return httpx.Response(
            409,
            json={
                "detail": "Turn request cannot be replayed",
            },
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistRequestStateError,
        match="cannot be replayed",
    ):
        await client.execute_conversation_turn(
            external_user_id="123",
            conversation_id=CONVERSATION_ID,
            request_id=TURN_REQUEST_ID,
            content="Retry failed request",
        )


@pytest.mark.anyio
async def test_memory_remember_sends_trusted_identity_without_confirmation():
    import json

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert request.method == "POST"
        assert (
            request.url.path
            == (
                "/api/v1/integrations/"
                "xynafaith/memory-actions/execute"
            )
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
            == "memory-user-1"
        )
        assert (
            "X-XynAssist-Action-Confirmed"
            not in request.headers
        )

        payload = json.loads(
            request.content.decode("utf-8")
        )

        assert payload == {
            "request_id":
                "11111111-1111-4111-8111-111111111111",
            "action_name": "memory.remember",
            "arguments": {
                "memory_type": "preference",
                "key": "response_style",
                "value": "concise",
            },
        }

        return httpx.Response(
            200,
            json={
                "memory_id": "memory-1",
                "memory_type": "preference",
                "key": "response_style",
                "status": "active",
            },
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    result = await client.execute_memory_action(
        external_user_id="memory-user-1",
        request_id=(
            "11111111-1111-4111-8111-111111111111"
        ),
        action_name="memory.remember",
        arguments={
            "memory_type": "preference",
            "key": "response_style",
            "value": "concise",
        },
    )

    assert result["status"] == "active"


@pytest.mark.anyio
async def test_memory_forget_sends_trusted_confirmation():
    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
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
            == "memory-user-2"
        )
        assert (
            request.headers[
                "X-XynAssist-Action-Confirmed"
            ]
            == "true"
        )

        return httpx.Response(
            200,
            json={
                "memory_id": "memory-2",
                "memory_type": "user_fact",
                "key": "preferred_translation",
                "status": "inactive",
            },
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    result = await client.execute_memory_action(
        external_user_id="memory-user-2",
        request_id=(
            "22222222-2222-4222-8222-222222222222"
        ),
        action_name="memory.forget",
        arguments={
            "memory_type": "user_fact",
            "key": "preferred_translation",
        },
        trusted_confirmed=True,
    )

    assert result["status"] == "inactive"


@pytest.mark.anyio
async def test_memory_action_arguments_cannot_create_confirmation_header():
    import json

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            "X-XynAssist-Action-Confirmed"
            not in request.headers
        )

        payload = json.loads(
            request.content.decode("utf-8")
        )

        assert payload["arguments"] == {
            "memory_type": "preference",
            "key": "response_style",
            "confirmed": True,
        }

        return httpx.Response(
            422,
            json={
                "detail":
                    "Invalid memory.forget arguments",
            },
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistResponseError,
        match="HTTP 422",
    ):
        await client.execute_memory_action(
            external_user_id="memory-user-3",
            request_id=(
                "33333333-3333-4333-8333-333333333333"
            ),
            action_name="memory.forget",
            arguments={
                "memory_type": "preference",
                "key": "response_style",
                "confirmed": True,
            },
            trusted_confirmed=False,
        )


@pytest.mark.anyio
async def test_memory_action_false_confirmation_omits_header():
    from api.services.xynassist_client import (
        XynAssistConflictError,
    )

    async def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        assert (
            "X-XynAssist-Action-Confirmed"
            not in request.headers
        )

        return httpx.Response(
            409,
            json={
                "detail":
                    "Trusted confirmation is required",
            },
        )

    client = XynAssistClient(
        base_url="https://xynassist.test",
        service_token="test-service-token",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(
        XynAssistConflictError,
        match="Trusted confirmation is required",
    ):
        await client.execute_memory_action(
            external_user_id="memory-user-4",
            request_id=(
                "44444444-4444-4444-8444-444444444444"
            ),
            action_name="memory.forget",
            arguments={
                "memory_type": "preference",
                "key": "response_style",
            },
            trusted_confirmed=False,
        )


@pytest.mark.anyio
async def test_memory_action_rejects_non_object_response():
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
        match="invalid memory action response shape",
    ):
        await client.execute_memory_action(
            external_user_id="memory-user-5",
            request_id=(
                "55555555-5555-4555-8555-555555555555"
            ),
            action_name="memory.remember",
            arguments={
                "memory_type": "preference",
                "key": "response_style",
                "value": "concise",
            },
        )
