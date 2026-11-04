"""
Model-provider registry for XynAssist.
"""

from __future__ import annotations

from threading import RLock

from xynassist_service.ai.contracts import ModelProvider


class ModelProviderNotRegistered(RuntimeError):
    """Requested model provider is not registered."""


_PROVIDERS: dict[str, ModelProvider] = {}
_LOCK = RLock()


def register_model_provider(
    provider: ModelProvider,
    *,
    replace: bool = False,
) -> None:
    name = provider.name.strip().lower()

    if not name:
        raise ValueError("Model provider name is required")

    with _LOCK:
        if name in _PROVIDERS and not replace:
            raise ValueError(
                f"Model provider already registered: {name}"
            )

        _PROVIDERS[name] = provider


def get_model_provider(name: str) -> ModelProvider:
    normalized = name.strip().lower()

    with _LOCK:
        provider = _PROVIDERS.get(normalized)

    if provider is None:
        raise ModelProviderNotRegistered(
            f"Model provider is not registered: {normalized}"
        )

    return provider


def clear_model_providers() -> None:
    """Test helper. Production code should not clear the registry."""

    with _LOCK:
        _PROVIDERS.clear()
