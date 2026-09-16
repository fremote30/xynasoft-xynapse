from __future__ import annotations

from types import SimpleNamespace

from xynassist_service.ai.contracts import (
    ModelMessage,
    ModelRequest,
)
from xynassist_service.ai.providers.openai_provider import (
    OpenAIModelProvider,
)


class FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)

        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content="  Grace and peace.  "
                    )
                )
            ],
            model="provider-model-v1",
            usage=SimpleNamespace(
                prompt_tokens=21,
                completion_tokens=7,
            ),
        )


def test_openai_provider_translates_model_contract():
    provider = OpenAIModelProvider(
        api_key="test-key",
        model="configured-model",
    )

    fake_completions = FakeCompletions()

    provider._client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=fake_completions,
        )
    )

    request = ModelRequest(
        messages=[
            ModelMessage(
                role="system",
                content="You are Xyniva.",
            ),
            ModelMessage(
                role="user",
                content="Explain grace.",
            ),
        ],
        temperature=0.2,
        max_output_tokens=900,
    )

    result = provider.generate(request)

    assert len(fake_completions.calls) == 1

    call = fake_completions.calls[0]

    assert "temperature" not in call

    assert call == {
        "model": "configured-model",
        "messages": [
            {
                "role": "system",
                "content": "You are Xyniva.",
            },
            {
                "role": "user",
                "content": "Explain grace.",
            },
        ],
        "max_completion_tokens": 900,
    }

    assert result.content == "Grace and peace."
    assert result.provider == "openai"
    assert result.model == "provider-model-v1"
    assert result.input_tokens == 21
    assert result.output_tokens == 7


def test_openai_provider_requires_api_key():
    try:
        OpenAIModelProvider(
            api_key="   ",
            model="configured-model",
        )
    except ValueError as exc:
        assert str(exc) == "OpenAI API key is required"
    else:
        raise AssertionError(
            "Expected missing API key to fail"
        )


def test_openai_provider_requires_model():
    try:
        OpenAIModelProvider(
            api_key="test-key",
            model="   ",
        )
    except ValueError as exc:
        assert str(exc) == "OpenAI model is required"
    else:
        raise AssertionError(
            "Expected missing model to fail"
        )
