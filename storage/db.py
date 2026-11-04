# storage/db.py
from __future__ import annotations

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

# Safe in local dev; in Docker we primarily rely on injected env vars.
# If .env exists in the container, loading it is okay because we will prefer DATABASE_URL explicitly.
load_dotenv(".env")

def _choose_db_url() -> str:
    """
    Choose DB URL in this order:

    If ENV=docker:
      1) DATABASE_URL (should be set by docker-compose)
      2) DATABASE_URL_DOCKER (legacy)
      3) DATABASE_URL (from .env fallback)

    Else (local/dev):
      1) DATABASE_URL_LOCAL
      2) DATABASE_URL
    """
    env = (os.getenv("ENV") or "").strip().lower()

    if env == "docker":
        db_url = (os.getenv("DATABASE_URL") or "").strip()
        if db_url:
            return db_url

        db_url_docker = (os.getenv("DATABASE_URL_DOCKER") or "").strip()
        if db_url_docker:
            return db_url_docker

        # fallback if someone only set DATABASE_URL in .env
        db_url = (os.getenv("DATABASE_URL") or "").strip()
        if db_url:
            return db_url

        raise RuntimeError("Docker ENV set but DATABASE_URL not provided")

    # local/dev
    db_url_local = (os.getenv("DATABASE_URL_LOCAL") or "").strip()
    if db_url_local:
        return db_url_local

    db_url = (os.getenv("DATABASE_URL") or "").strip()
    if db_url:
        return db_url

    raise RuntimeError("DATABASE_URL_LOCAL or DATABASE_URL not set")

DATABASE_URL: str = _choose_db_url()

engine: Engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
)

