# auth/api_key.py
from __future__ import annotations

import os
from dotenv import load_dotenv
from fastapi import Header, HTTPException

# Ensure .env is loaded even when uvicorn reloads
load_dotenv(".env")


def require_api_key(x_api_key: str | None = Header(default=None, alias="x-api-key")) -> bool:
    expected = os.getenv("API_KEY")

    if not expected:
        raise HTTPException(status_code=500, detail="Server misconfigured: API_KEY is not set")

    if not x_api_key or x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

    return True
