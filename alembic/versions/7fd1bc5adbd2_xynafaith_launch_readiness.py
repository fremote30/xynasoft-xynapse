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

    # ============================================================
    # LEGACY XYNAFAITH FOUNDATION
    # ============================================================
    # Early XynaFaith application tables originally existed outside
    # the Alembic migration history. Production databases therefore
    # already contain them, while a clean database does not.
    #
    # Create only the historical minimum schema here when missing.
    # Later migrations remain responsible for adding newer columns.
    # ============================================================

    if "churches" not in existing_tables:
        op.create_table(
            "churches",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("location", sa.String(), nullable=True),
        )

    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "users" not in existing_tables:
        op.create_table(
            "users",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("password", sa.String(), nullable=False),
            sa.Column("role", sa.String(), nullable=True),
            sa.Column("is_verified", sa.Boolean(), nullable=True),
            sa.Column(
                "church_id",
                sa.Integer(),
                sa.ForeignKey("churches.id"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_users_id", "users", ["id"], unique=False)
        op.create_index("ix_users_email", "users", ["email"], unique=True)

    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "sermons" not in existing_tables:
        op.create_table(
            "sermons",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("content", sa.Text(), nullable=True),
            sa.Column(
                "author_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("is_public", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("views", sa.Integer(), nullable=True),
            sa.Column("shares", sa.Integer(), nullable=True),
        )
        op.create_index("ix_sermons_id", "sermons", ["id"], unique=False)

    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "refresh_tokens" not in existing_tables:
        op.create_table(
            "refresh_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("token", sa.String(), nullable=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column(
                "is_revoked",
                sa.Boolean(),
                nullable=True,
                server_default=sa.text("false"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=True,
                server_default=sa.text("now()"),
            ),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
        )

    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "pastor_members" not in existing_tables:
        op.create_table(
            "pastor_members",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "pastor_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column(
                "member_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint(
                "pastor_id",
                "member_id",
                name="unique_follow",
            ),
        )
        op.create_index(
            "ix_pastor_members_id",
            "pastor_members",
            ["id"],
            unique=False,
        )

    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "pastor_profiles" not in existing_tables:
        op.create_table(
            "pastor_profiles",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            sa.Column("bio", sa.Text(), nullable=True),
            sa.Column("church_name", sa.String(), nullable=True),
            sa.Column("ministry_focus", sa.String(), nullable=True),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("website", sa.String(), nullable=True),
            sa.Column("profile_image", sa.String(), nullable=True),
            sa.Column("cover_image", sa.String(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_pastor_profiles_id",
            "pastor_profiles",
            ["id"],
            unique=False,
        )

    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "pastor_followers" not in existing_tables:
        op.create_table(
            "pastor_followers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "member_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "pastor_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=True,
            ),
        )
        op.create_index(
            "ix_pastor_followers_id",
            "pastor_followers",
            ["id"],
            unique=False,
        )

    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "shared_sermons" not in existing_tables:
        op.create_table(
            "shared_sermons",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "sermon_id",
                sa.Integer(),
                sa.ForeignKey("sermons.id"),
                nullable=False,
            ),
            sa.Column(
                "from_pastor_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column(
                "to_pastor_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("comment", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index(
            "ix_shared_sermons_id",
            "shared_sermons",
            ["id"],
            unique=False,
        )

    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "sermon_comments" not in existing_tables:
        op.create_table(
            "sermon_comments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "sermon_id",
                sa.Integer(),
                sa.ForeignKey("sermons.id"),
                nullable=False,
            ),
            sa.Column(
                "pastor_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("comment", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )
        op.create_index(
            "ix_sermon_comments_id",
            "sermon_comments",
            ["id"],
            unique=False,
        )

    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "prayers" not in existing_tables:
        op.create_table(
            "prayers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
            ),
            sa.Column("message", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    # Refresh the inspector before the existing launch-readiness work.
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