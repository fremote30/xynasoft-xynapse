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

    CONVERSATIONS_PATH = (
        "/api/v1/integrations/xynafaith/conversations"
    )

    EXTERNAL_USER_HEADER = (
        "X-XynAssist-External-User-Id"
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

    def _trusted_headers(
        self,
        *,
        external_user_id: str | None = None,
    ) -> dict[str, str]:
        """
        Build headers for a trusted XynAssist request.

        Product-user identity is accepted only from
        XynaFaith server-side callers.
        """

        if not self.service_token:
            raise XynAssistConfigurationError(
                "XynAssist service authentication "
                "is not configured"
            )

        headers = {
            self.SERVICE_TOKEN_HEADER:
                self.service_token,
        }

        if external_user_id is not None:
            normalized = external_user_id.strip()

            if not normalized:
                raise XynAssistConfigurationError(
                    "XynAssist external user "
                    "identifier is required"
                )

            headers[
                self.EXTERNAL_USER_HEADER
            ] = normalized

        return headers

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        external_user_id: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        """
        Execute one trusted XynAssist JSON request.
        """

        headers = self._trusted_headers(
            external_user_id=external_user_id,
        )

        url = f"{self.base_url}{path}"

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.request(
                    method,
                    url,
                    json=payload,
                    headers=headers,
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
            return response.json()
        except ValueError as exc:
            raise XynAssistResponseError(
                "XynAssist returned invalid JSON"
            ) from exc

    async def create_conversation(
        self,
        *,
        external_user_id: str,
        title: str | None = None,
    ) -> dict[str, Any]:
        """
        Create a trusted XynaFaith conversation.
        """

        data = await self._request_json(
            "POST",
            self.CONVERSATIONS_PATH,
            external_user_id=external_user_id,
            payload={
                "title": title,
            },
        )

        if not isinstance(data, dict):
            raise XynAssistResponseError(
                "XynAssist returned an invalid "
                "response shape"
            )

        return data

    async def list_conversations(
        self,
        *,
        external_user_id: str,
    ) -> list[dict[str, Any]]:
        """
        List conversations owned by one XynaFaith user.
        """

        data = await self._request_json(
            "GET",
            self.CONVERSATIONS_PATH,
            external_user_id=external_user_id,
        )

        if (
            not isinstance(data, list)
            or not all(
                isinstance(item, dict)
                for item in data
            )
        ):
            raise XynAssistResponseError(
                "XynAssist returned an invalid "
                "response shape"
            )

        return data

    async def get_conversation(
        self,
        *,
        external_user_id: str,
        conversation_id: str,
    ) -> dict[str, Any]:
        """
        Get one externally owned conversation.
        """

        path = (
            f"{self.CONVERSATIONS_PATH}/"
            f"{conversation_id}"
        )

        data = await self._request_json(
            "GET",
            path,
            external_user_id=external_user_id,
        )

        if not isinstance(data, dict):
            raise XynAssistResponseError(
                "XynAssist returned an invalid "
                "response shape"
            )

        return data

    async def execute_conversation_turn(
        self,
        *,
        external_user_id: str,
        conversation_id: str,
        content: str,
    ) -> dict[str, Any]:
        """
        Execute one conversational XynaFaith turn.
        """

        path = (
            f"{self.CONVERSATIONS_PATH}/"
            f"{conversation_id}/turns"
        )

        data = await self._request_json(
            "POST",
            path,
            external_user_id=external_user_id,
            payload={
                "content": content,
            },
        )

        if not isinstance(data, dict):
            raise XynAssistResponseError(
                "XynAssist returned an invalid "
                "response shape"
            )

        return data
