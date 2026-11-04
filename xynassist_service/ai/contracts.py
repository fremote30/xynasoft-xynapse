"""
Provider-independent AI contracts for XynAssist.

Domain orchestration depends on these contracts rather than directly
depending on OpenAI, Anthropic, or another model vendor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass(frozen=True)
class ModelMessage:
    role: str
    content: str


@dataclass(frozen=True)
class ModelRequest:
    messages: Sequence[ModelMessage]
    temperature: float = 0.2
    max_output_tokens: int = 1200


@dataclass(frozen=True)
class ModelResponse:
    content: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class ModelProvider(Protocol):
    """Contract implemented by every XynAssist model provider."""

    @property
    def name(self) -> str:
        ...

    def generate(self, request: ModelRequest) -> ModelResponse:
        ...
