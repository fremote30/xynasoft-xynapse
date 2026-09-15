from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from xynassist_service.ai.contracts import (
    ModelRequest,
    ModelResponse,
)
from xynassist_service.ai.registry import (
    ModelProviderNotRegistered,
    clear_model_providers,
    register_model_provider,
)
from xynassist_service.xyniva.orchestrator import (
    execute_xyniva_turn,
)


@dataclass
class FakeProvider:
    response_content: str = "Grace and peace."
    requests: list[ModelRequest] = field(
        default_factory=list
    )

    @property
    def name(self) -> str:
        return "fake"

    def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        self.requests.append(request)

        return ModelResponse(
            content=self.response_content,
            provider=self.name,
            model="fake-model-v1",
            input_tokens=10,
            output_tokens=5,
        )


@pytest.fixture(autouse=True)
def reset_provider_registry():
    clear_model_providers()

    yield

    clear_model_providers()


def test_xyniva_uses_registered_provider():
    provider = FakeProvider(
        response_content="Here is a helpful response."
    )

    register_model_provider(provider)

    result = execute_xyniva_turn(
        content="Help me understand grace.",
        context=None,
        provider_name="fake",
    )

    assert result.content == "Here is a helpful response."
    assert result.skill == "conversation.respond"
    assert result.provider == "fake"
    assert result.model == "fake-model-v1"

    assert len(provider.requests) == 1

    request = provider.requests[0]

    assert request.messages[0].role == "system"
    assert "You are Xyniva" in request.messages[0].content

    assert request.messages[-1].role == "user"
    assert (
        request.messages[-1].content
        == "Help me understand grace."
    )


def test_xyniva_passes_only_allowlisted_context():
    provider = FakeProvider()

    register_model_provider(provider)

    execute_xyniva_turn(
        content="Prepare some ideas.",
        context={
            "denomination": "Methodist",
            "audience": "Youth",
            "language": "English",
            "church_name": "Grace Church",
            "secret_internal_value": "do-not-send",
        },
        provider_name="fake",
    )

    request = provider.requests[0]

    combined = "\n".join(
        message.content
        for message in request.messages
    )

    assert "Methodist" in combined
    assert "Youth" in combined
    assert "English" in combined
    assert "Grace Church" in combined
    assert "secret_internal_value" not in combined
    assert "do-not-send" not in combined


def test_xyniva_rejects_blank_user_content():
    provider = FakeProvider()

    register_model_provider(provider)

    with pytest.raises(
        ValueError,
        match="Turn content is required",
    ):
        execute_xyniva_turn(
            content="   ",
            context=None,
            provider_name="fake",
        )

    assert provider.requests == []


def test_xyniva_rejects_empty_provider_response():
    provider = FakeProvider(
        response_content="   "
    )

    register_model_provider(provider)

    with pytest.raises(
        RuntimeError,
        match="empty response",
    ):
        execute_xyniva_turn(
            content="Hello",
            context=None,
            provider_name="fake",
        )


def test_xyniva_fails_closed_for_unknown_provider():
    with pytest.raises(
        ModelProviderNotRegistered,
        match="not registered",
    ):
        execute_xyniva_turn(
            content="Hello",
            context=None,
            provider_name="missing",
        )


def test_duplicate_provider_registration_fails():
    register_model_provider(FakeProvider())

    with pytest.raises(
        ValueError,
        match="already registered",
    ):
        register_model_provider(
            FakeProvider()
        )
