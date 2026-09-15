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
