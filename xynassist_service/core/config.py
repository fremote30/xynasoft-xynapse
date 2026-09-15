"""
Configuration for the standalone XynAssist service.

XynAssist is a trusted internal platform service. Product
applications such as XynaFaith authenticate to it using a
service credential. Product-user identity is supplied only
through trusted server-to-server requests.
"""

from __future__ import annotations

import os


def _required_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(
            f"{name} environment variable is required"
        )

    return value


def get_service_token() -> str:
    """
    Return the credential trusted product services must use.

    Read lazily so importing the application does not expose or
    materialize the credential unnecessarily.
    """

    return _required_env("XYNASSIST_SERVICE_TOKEN")


def get_model_provider_name() -> str:
    """
    Return the configured XynAssist model provider.

    Provider selection belongs to XynAssist rather than a product
    application such as XynaFaith.
    """

    return _required_env(
        "XYNASSIST_MODEL_PROVIDER"
    ).lower()


def get_openai_api_key() -> str:
    """Return the OpenAI credential used by XynAssist."""

    return _required_env("OPENAI_API_KEY")


def get_openai_model() -> str:
    """Return the OpenAI model configured for XynAssist."""

    return _required_env(
        "XYNASSIST_OPENAI_MODEL"
    )
