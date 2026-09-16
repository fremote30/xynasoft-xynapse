"""
Independent Alembic environment for XynAssist.

This migration graph must never operate on the XynaFaith
database.
"""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from xynassist_service.db.database import Base

# Import models so SQLAlchemy metadata is complete.
from xynassist_service.models import (  # noqa: F401
    ActionExecution,
    Conversation,
    ConversationMessage,
    ConversationTurn,
    Memory,
)


config = context.config


database_url = (
    os.getenv("XYNASSIST_DATABASE_URL", "")
    .strip()
)

if not database_url:
    raise RuntimeError(
        "XYNASSIST_DATABASE_URL environment variable "
        "is required"
    )


config.set_main_option(
    "sqlalchemy.url",
    database_url,
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(
            config.config_ini_section,
            {}
        ),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
