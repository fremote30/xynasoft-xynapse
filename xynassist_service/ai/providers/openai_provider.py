"""
OpenAI model-provider adapter for XynAssist.

This module translates the provider-independent XynAssist model
contract into the OpenAI SDK contract. Xyniva orchestration must not
depend directly on the OpenAI SDK.
"""

from __future__ import annotations

from openai import OpenAI

from xynassist_service.ai.contracts import (
    ModelRequest,
    ModelResponse,
)


class OpenAIModelProvider:
    """OpenAI implementation of the XynAssist model-provider contract."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
    ) -> None:
        api_key = api_key.strip()
        model = model.strip()

        if not api_key:
            raise ValueError("OpenAI API key is required")

        if not model:
            raise ValueError("OpenAI model is required")

        self._client = OpenAI(api_key=api_key)
        self._model = model

    @property
    def name(self) -> str:
        return "openai"

    def generate(
        self,
        request: ModelRequest,
    ) -> ModelResponse:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": message.role,
                    "content": message.content,
                }
                for message in request.messages
            ],
            temperature=request.temperature,
            max_tokens=request.max_output_tokens,
        )

        if not response.choices:
            raise RuntimeError(
                "OpenAI returned no completion choices"
            )

        content = response.choices[0].message.content

        if not content or not content.strip():
            raise RuntimeError(
                "OpenAI returned an empty completion"
            )

        usage = response.usage

        return ModelResponse(
            content=content.strip(),
            provider=self.name,
            model=response.model or self._model,
            input_tokens=(
                usage.prompt_tokens
                if usage is not None
                else None
            ),
            output_tokens=(
                usage.completion_tokens
                if usage is not None
                else None
            ),
        )
