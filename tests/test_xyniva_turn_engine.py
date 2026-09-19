from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from xynassist_service.ai.contracts import (
    ModelRequest,
    ModelResponse,
)
from xynassist_service.ai.registry import (
    clear_model_providers,
    register_model_provider,
)
from xynassist_service.services.turn_engine import (
    execute_turn_engine,
)


@dataclass
class FakeProvider:
    response_content: str = "Xyniva response"
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
            provider="fake",
            model="fake-model-v1",
        )


@pytest.fixture(autouse=True)
def reset_registry(monkeypatch):
    clear_model_providers()

    monkeypatch.setenv(
        "XYNASSIST_MODEL_PROVIDER",
        "fake",
    )

    yield

    clear_model_providers()


def test_turn_engine_executes_xyniva_orchestrator(
    monkeypatch,
):
    provider = FakeProvider(
        response_content=(
            '{"kind":"response",'
            '"content":"Grace is central to the Christian message."}'
        )
    )

    register_model_provider(provider)

    result = execute_turn_engine(
        content="Explain grace.",
        context={
            "denomination": "Methodist",
        },
    )

    assert (
        result.content
        == "Grace is central to the Christian message."
    )
    assert result.skill == "conversation.respond"
    assert result.action is None
    assert result.prompt is None

    assert len(provider.requests) == 1

    request = provider.requests[0]

    assert request.messages[-1].role == "user"
    assert request.messages[-1].content == "Explain grace."


def test_turn_engine_fails_closed_without_provider_config(
    monkeypatch,
):
    monkeypatch.delenv(
        "XYNASSIST_MODEL_PROVIDER",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "XYNASSIST_MODEL_PROVIDER "
            "environment variable is required"
        ),
    ):
        execute_turn_engine(
            content="Hello",
            context=None,
        )


def test_turn_engine_does_not_fallback_when_provider_missing():
    with pytest.raises(
        RuntimeError,
        match="Unsupported XynAssist model provider: fake",
    ):
        execute_turn_engine(
            content="Hello",
            context=None,
        )
