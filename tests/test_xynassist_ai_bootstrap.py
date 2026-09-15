from __future__ import annotations

import pytest

from xynassist_service.ai.bootstrap import (
    UnsupportedModelProvider,
    get_configured_model_provider,
)
from xynassist_service.ai.registry import (
    clear_model_providers,
)


@pytest.fixture(autouse=True)
def reset_registry():
    clear_model_providers()

    yield

    clear_model_providers()


def test_bootstrap_requires_provider_configuration(
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
        get_configured_model_provider()


def test_bootstrap_rejects_unsupported_provider(
    monkeypatch,
):
    monkeypatch.setenv(
        "XYNASSIST_MODEL_PROVIDER",
        "unknown",
    )

    with pytest.raises(
        UnsupportedModelProvider,
        match="Unsupported XynAssist model provider: unknown",
    ):
        get_configured_model_provider()


def test_openai_bootstrap_requires_api_key(
    monkeypatch,
):
    monkeypatch.setenv(
        "XYNASSIST_MODEL_PROVIDER",
        "openai",
    )

    monkeypatch.delenv(
        "OPENAI_API_KEY",
        raising=False,
    )

    monkeypatch.setenv(
        "XYNASSIST_OPENAI_MODEL",
        "test-model",
    )

    with pytest.raises(
        RuntimeError,
        match="OPENAI_API_KEY environment variable is required",
    ):
        get_configured_model_provider()


def test_openai_bootstrap_requires_model(
    monkeypatch,
):
    monkeypatch.setenv(
        "XYNASSIST_MODEL_PROVIDER",
        "openai",
    )

    monkeypatch.setenv(
        "OPENAI_API_KEY",
        "test-key",
    )

    monkeypatch.delenv(
        "XYNASSIST_OPENAI_MODEL",
        raising=False,
    )

    with pytest.raises(
        RuntimeError,
        match=(
            "XYNASSIST_OPENAI_MODEL "
            "environment variable is required"
        ),
    ):
        get_configured_model_provider()
