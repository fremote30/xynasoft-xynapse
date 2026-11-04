from __future__ import annotations
import os
from fastapi import Header, HTTPException

def require_api_key(x_api_key: str | None = Header(default=None)):
    auth_enabled = os.getenv("AUTH_ENABLED", "false").lower() == "true"
    if not auth_enabled:
        return

    expected = os.getenv("API_KEY")
    if not expected:
        raise HTTPException(status_code=500, detail="AUTH_ENABLED=true but API_KEY is not set")

    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
