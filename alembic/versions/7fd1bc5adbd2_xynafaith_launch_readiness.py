"""xynafaith launch readiness

Revision ID: 7fd1bc5adbd2
Revises: e3d7e3f9897a
Create Date: 2026-06-01 15:59:09.161397
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect


revision: str = "7fd1bc5adbd2"
down_revision: Union[str, Sequence[str], None] = "e3d7e3f9897a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    # USERS
    if "users" in existing_tables:
        if not _column_exists(inspector, "users", "pastor_status"):
            op.add_column(
                "users",
                sa.Column(
                    "pastor_status",
                    sa.String(length=20),
                    nullable=False,
                    server_default="member",
                ),
            )

        if not _column_exists(inspector, "users", "pastor_application_date"):
            op.add_column(
                "users",
                sa.Column("pastor_application_date", sa.DateTime(), nullable=True),
            )

        if not _column_exists(inspector, "users", "pastor_review_date"):
            op.add_column(
                "users",
                sa.Column("pastor_review_date", sa.DateTime(), nullable=True),
            )

        if not _column_exists(inspector, "users", "pastor_review_notes"):
            op.add_column(
                "users",
                sa.Column("pastor_review_notes", sa.Text(), nullable=True),
            )

    # SERMONS
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "sermons" in existing_tables:
        if not _column_exists(inspector, "sermons", "sermon_data"):
            op.add_column(
                "sermons",
                sa.Column(
                    "sermon_data",
                    postgresql.JSONB(astext_type=sa.Text()),
                    nullable=True,
                ),
            )

    # NOTIFICATIONS
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "notifications" not in existing_tables:
        op.create_table(
            "notifications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("type", sa.String(length=50), nullable=True),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column(
                "is_read",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

    # PRAYER REACTIONS
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "prayer_reactions" not in existing_tables:
        op.create_table(
            "prayer_reactions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("prayer_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("reaction_type", sa.String(length=20), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "prayer_reactions" in existing_tables:
        op.drop_table("prayer_reactions")

    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "notifications" in existing_tables:
        op.drop_table("notifications")

    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "sermons" in existing_tables and _column_exists(inspector, "sermons", "sermon_data"):
        op.drop_column("sermons", "sermon_data")

    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "users" in existing_tables:
        if _column_exists(inspector, "users", "pastor_review_notes"):
            op.drop_column("users", "pastor_review_notes")

        if _column_exists(inspector, "users", "pastor_review_date"):
            op.drop_column("users", "pastor_review_date")

        if _column_exists(inspector, "users", "pastor_application_date"):
            op.drop_column("users", "pastor_application_date")

        if _column_exists(inspector, "users", "pastor_status"):
            op.drop_column("users", "pastor_status")