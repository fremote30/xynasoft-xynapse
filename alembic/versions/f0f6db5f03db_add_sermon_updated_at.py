"""add sermon updated_at

Revision ID: f0f6db5f03db
Revises: 7fd1bc5adbd2
Create Date: 2026-06-20 10:01:49.414141
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision: str = "f0f6db5f03db"
down_revision: Union[str, Sequence[str], None] = "7fd1bc5adbd2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def _fk_exists(inspector, table_name: str, constrained_columns: list[str], referred_table: str) -> bool:
    for fk in inspector.get_foreign_keys(table_name):
        if fk.get("constrained_columns") == constrained_columns and fk.get("referred_table") == referred_table:
            return True
    return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    # Do NOT drop notifications or prayer_reactions here.
    # They were created in the previous migration and are part of XynaFaith launch readiness.

    # Create pastors table only if missing.
    if "pastors" not in existing_tables:
        op.create_table(
            "pastors",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("password", sa.String(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    inspector = inspect(bind)

    if "pastors" in inspector.get_table_names():
        if not _index_exists(inspector, "pastors", "ix_pastors_email"):
            op.create_index("ix_pastors_email", "pastors", ["email"], unique=True)

        if not _index_exists(inspector, "pastors", "ix_pastors_id"):
            op.create_index("ix_pastors_id", "pastors", ["id"], unique=False)

    # Prayers indexes and message type adjustment
    inspector = inspect(bind)

    if "prayers" in inspector.get_table_names():
        if not _index_exists(inspector, "prayers", "ix_prayers_created_at"):
            op.create_index("ix_prayers_created_at", "prayers", ["created_at"], unique=False)

        if not _index_exists(inspector, "prayers", "ix_prayers_id"):
            op.create_index("ix_prayers_id", "prayers", ["id"], unique=False)

        if _column_exists(inspector, "prayers", "message"):
            op.alter_column(
                "prayers",
                "message",
                existing_type=sa.VARCHAR(),
                type_=sa.Text(),
                existing_nullable=False,
            )

    # refresh_tokens token nullable fix
    inspector = inspect(bind)

    if "refresh_tokens" in inspector.get_table_names():
        if _column_exists(inspector, "refresh_tokens", "token"):
            op.alter_column(
                "refresh_tokens",
                "token",
                existing_type=sa.VARCHAR(),
                nullable=False,
            )

    # sermon_comments indexes and foreign keys
    inspector = inspect(bind)

    if "sermon_comments" in inspector.get_table_names():
        if not _index_exists(inspector, "sermon_comments", "ix_sermon_comments_created_at"):
            op.create_index(
                "ix_sermon_comments_created_at",
                "sermon_comments",
                ["created_at"],
                unique=False,
            )

        if not _index_exists(inspector, "sermon_comments", "ix_sermon_comments_pastor_id"):
            op.create_index(
                "ix_sermon_comments_pastor_id",
                "sermon_comments",
                ["pastor_id"],
                unique=False,
            )

        if not _index_exists(inspector, "sermon_comments", "ix_sermon_comments_sermon_id"):
            op.create_index(
                "ix_sermon_comments_sermon_id",
                "sermon_comments",
                ["sermon_id"],
                unique=False,
            )

        if (
            "sermons" in inspector.get_table_names()
            and _column_exists(inspector, "sermon_comments", "sermon_id")
            and not _fk_exists(inspector, "sermon_comments", ["sermon_id"], "sermons")
        ):
            op.create_foreign_key(
                "fk_sermon_comments_sermon_id_sermons",
                "sermon_comments",
                "sermons",
                ["sermon_id"],
                ["id"],
            )

        if (
            "users" in inspector.get_table_names()
            and _column_exists(inspector, "sermon_comments", "pastor_id")
            and not _fk_exists(inspector, "sermon_comments", ["pastor_id"], "users")
        ):
            op.create_foreign_key(
                "fk_sermon_comments_pastor_id_users",
                "sermon_comments",
                "users",
                ["pastor_id"],
                ["id"],
            )

    # sermons updated_at + indexes
    inspector = inspect(bind)

    if "sermons" in inspector.get_table_names():
        if not _column_exists(inspector, "sermons", "updated_at"):
            op.add_column("sermons", sa.Column("updated_at", sa.DateTime(), nullable=True))

        if _column_exists(inspector, "sermons", "title"):
            op.alter_column(
                "sermons",
                "title",
                existing_type=sa.VARCHAR(),
                nullable=False,
            )

        if not _index_exists(inspector, "sermons", "ix_sermons_created_at"):
            op.create_index("ix_sermons_created_at", "sermons", ["created_at"], unique=False)

    # shared_sermons indexes
    inspector = inspect(bind)

    if "shared_sermons" in inspector.get_table_names():
        if not _index_exists(inspector, "shared_sermons", "ix_shared_sermons_created_at"):
            op.create_index(
                "ix_shared_sermons_created_at",
                "shared_sermons",
                ["created_at"],
                unique=False,
            )

        if not _index_exists(inspector, "shared_sermons", "ix_shared_sermons_from_pastor_id"):
            op.create_index(
                "ix_shared_sermons_from_pastor_id",
                "shared_sermons",
                ["from_pastor_id"],
                unique=False,
            )

        if not _index_exists(inspector, "shared_sermons", "ix_shared_sermons_sermon_id"):
            op.create_index(
                "ix_shared_sermons_sermon_id",
                "shared_sermons",
                ["sermon_id"],
                unique=False,
            )

        if not _index_exists(inspector, "shared_sermons", "ix_shared_sermons_to_pastor_id"):
            op.create_index(
                "ix_shared_sermons_to_pastor_id",
                "shared_sermons",
                ["to_pastor_id"],
                unique=False,
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "shared_sermons" in inspector.get_table_names():
        if _index_exists(inspector, "shared_sermons", "ix_shared_sermons_to_pastor_id"):
            op.drop_index("ix_shared_sermons_to_pastor_id", table_name="shared_sermons")
        if _index_exists(inspector, "shared_sermons", "ix_shared_sermons_sermon_id"):
            op.drop_index("ix_shared_sermons_sermon_id", table_name="shared_sermons")
        if _index_exists(inspector, "shared_sermons", "ix_shared_sermons_from_pastor_id"):
            op.drop_index("ix_shared_sermons_from_pastor_id", table_name="shared_sermons")
        if _index_exists(inspector, "shared_sermons", "ix_shared_sermons_created_at"):
            op.drop_index("ix_shared_sermons_created_at", table_name="shared_sermons")

    inspector = inspect(bind)

    if "sermons" in inspector.get_table_names():
        if _index_exists(inspector, "sermons", "ix_sermons_created_at"):
            op.drop_index("ix_sermons_created_at", table_name="sermons")
        if _column_exists(inspector, "sermons", "updated_at"):
            op.drop_column("sermons", "updated_at")

    inspector = inspect(bind)

    if "sermon_comments" in inspector.get_table_names():
        if _index_exists(inspector, "sermon_comments", "ix_sermon_comments_sermon_id"):
            op.drop_index("ix_sermon_comments_sermon_id", table_name="sermon_comments")
        if _index_exists(inspector, "sermon_comments", "ix_sermon_comments_pastor_id"):
            op.drop_index("ix_sermon_comments_pastor_id", table_name="sermon_comments")
        if _index_exists(inspector, "sermon_comments", "ix_sermon_comments_created_at"):
            op.drop_index("ix_sermon_comments_created_at", table_name="sermon_comments")

    inspector = inspect(bind)

    if "prayers" in inspector.get_table_names():
        if _index_exists(inspector, "prayers", "ix_prayers_id"):
            op.drop_index("ix_prayers_id", table_name="prayers")
        if _index_exists(inspector, "prayers", "ix_prayers_created_at"):
            op.drop_index("ix_prayers_created_at", table_name="prayers")

    inspector = inspect(bind)

    if "pastors" in inspector.get_table_names():
        if _index_exists(inspector, "pastors", "ix_pastors_id"):
            op.drop_index("ix_pastors_id", table_name="pastors")
        if _index_exists(inspector, "pastors", "ix_pastors_email"):
            op.drop_index("ix_pastors_email", table_name="pastors")
        op.drop_table("pastors")