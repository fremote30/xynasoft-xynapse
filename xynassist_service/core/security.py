"""
Trusted server-to-server authentication for XynAssist.
"""

from __future__ import annotations

import hmac

from fastapi import Header, HTTPException, status

from xynassist_service.core.config import get_service_token


SERVICE_TOKEN_HEADER = "X-XynAssist-Service-Token"
EXTERNAL_USER_HEADER = "X-XynAssist-External-User-Id"


def require_service_auth(
    x_xynassist_service_token: str | None = Header(
        default=None,
        alias=SERVICE_TOKEN_HEADER,
    ),
) -> None:
    """
    Authenticate a trusted product service.

    Failure is intentionally indistinguishable between a missing
    and incorrect credential.
    """

    expected = get_service_token()
    supplied = (
        x_xynassist_service_token or ""
    ).strip()

    if not supplied or not hmac.compare_digest(
        supplied,
        expected,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid service credential",
        )


def require_external_user(
    x_xynassist_external_user_id: str | None = Header(
        default=None,
        alias=EXTERNAL_USER_HEADER,
    ),
) -> str:
    """
    Resolve the product-user identity supplied by the trusted
    product backend.

    XynAssist never accepts browser identity as authoritative.
    """

    external_user_id = (
        x_xynassist_external_user_id or ""
    ).strip()

    if not external_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="External user identifier is required",
        )

    return external_user_id
