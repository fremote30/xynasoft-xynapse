"""
Database foundation for the standalone XynAssist service.

XynAssist intentionally has its own database configuration
and SQLAlchemy metadata boundary so it can be deployed and
migrated independently from XynaFaith.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def get_database_url() -> str:
    database_url = (
        os.getenv("XYNASSIST_DATABASE_URL", "")
        .strip()
    )

    if not database_url:
        raise RuntimeError(
            "XYNASSIST_DATABASE_URL environment variable "
            "is required"
        )

    return database_url


DATABASE_URL = get_database_url()

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
