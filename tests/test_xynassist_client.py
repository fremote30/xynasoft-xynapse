from __future__ import annotations

import httpx
import pytest

from api.services.xynassist_client import (
    XynAssistClient,
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
