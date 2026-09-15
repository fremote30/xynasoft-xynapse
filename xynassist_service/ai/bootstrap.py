"""
Model-provider bootstrap for XynAssist.

Configuration selects a provider. This module constructs and
registers the corresponding adapter without exposing provider
details to Xyniva orchestration.
"""

from __future__ import annotations

from xynassist_service.ai.providers.openai_provider import (
    OpenAIModelProvider,
)
from xynassist_service.ai.registry import (
    ModelProviderNotRegistered,
    get_model_provider,
    register_model_provider,
)
from xynassist_service.core.config import (
    get_model_provider_name,
    get_openai_api_key,
    get_openai_model,
)


class UnsupportedModelProvider(RuntimeError):
    """Configured provider is not supported by this deployment."""


def _build_provider(provider_name: str):
    if provider_name == "openai":
        return OpenAIModelProvider(
            api_key=get_openai_api_key(),
            model=get_openai_model(),
        )

    raise UnsupportedModelProvider(
        f"Unsupported XynAssist model provider: "
        f"{provider_name}"
    )


def get_configured_model_provider():
    """
    Return the configured provider, registering it lazily.

    Lazy initialization prevents API credentials from being required
    merely to import the XynAssist application.
    """

    provider_name = get_model_provider_name()

    try:
        return get_model_provider(provider_name)
    except ModelProviderNotRegistered:
        pass

    provider = _build_provider(provider_name)

    register_model_provider(provider)

    return provider
