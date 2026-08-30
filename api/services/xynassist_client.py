from __future__ import annotations

from typing import Any

import httpx

from api.core.config import (
    XYNASSIST_BASE_URL,
    XYNASSIST_SERVICE_TOKEN,
    XYNASSIST_TIMEOUT_SECONDS,
)


class XynAssistError(RuntimeError):
    """Base error raised by the XynAssist integration client."""


class XynAssistConfigurationError(XynAssistError):
    """Raised when required XynAssist configuration is missing."""


class XynAssistUnavailableError(XynAssistError):
    """Raised when XynAssist cannot be reached."""


class XynAssistResponseError(XynAssistError):
    """Raised when XynAssist returns an invalid or unsuccessful response."""


class XynAssistClient:
    """
    HTTP boundary between XynaFaith and XynAssist.

    XynaFaith authenticates its own users. This client uses
    a separate backend-to-backend credential when invoking
    trusted XynAssist integration endpoints.
    """

    SERMON_GENERATE_PATH = (
        "/api/v1/integrations/xynafaith/sermons/generate"
    )

    SERVICE_TOKEN_HEADER = (
        "X-XynAssist-Service-Token"
    )

    def __init__(
        self,
        *,
        base_url: str = XYNASSIST_BASE_URL,
        timeout_seconds: float = XYNASSIST_TIMEOUT_SECONDS,
        service_token: str = XYNASSIST_SERVICE_TOKEN,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.service_token = service_token.strip()
        self.transport = transport

    async def generate_sermon(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Send an existing XynaFaith sermon request to XynAssist.

        The payload intentionally mirrors XynaFaith's current
        public SermonRequest contract so web/mobile clients
        do not need to change.
        """

        if not self.service_token:
            raise XynAssistConfigurationError(
                "XynAssist service authentication "
                "is not configured"
            )

        url = (
            f"{self.base_url}"
            f"{self.SERMON_GENERATE_PATH}"
        )

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={
                        self.SERVICE_TOKEN_HEADER:
                            self.service_token,
                    },
                )
        except httpx.RequestError as exc:
            raise XynAssistUnavailableError(
                "Unable to reach XynAssist"
            ) from exc

        if not response.is_success:
            raise XynAssistResponseError(
                f"XynAssist returned HTTP "
                f"{response.status_code}"
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise XynAssistResponseError(
                "XynAssist returned invalid JSON"
            ) from exc

        if not isinstance(data, dict):
            raise XynAssistResponseError(
                "XynAssist returned an invalid response shape"
            )

        return data
