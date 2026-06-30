"""add prayer wall engagement tables

Revision ID: 30dec66b204d
Revises: f0f6db5f03db
Create Date: 2026-06-29 06:22:20.749223
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "30dec66b204d"
down_revision: Union[str, Sequence[str], None] = "f0f6db5f03db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # =========================
    # ENGAGEMENT TABLES
    # =========================
    op.create_table(
        "prayer_bookmarks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prayer_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["prayer_id"], ["prayers.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "prayer_id",
            "user_id",
            name="uq_prayer_user_bookmark"
        ),
    )

    op.create_index(op.f("ix_prayer_bookmarks_id"), "prayer_bookmarks", ["id"], unique=False)
    op.create_index(op.f("ix_prayer_bookmarks_prayer_id"), "prayer_bookmarks", ["prayer_id"], unique=False)
    op.create_index(op.f("ix_prayer_bookmarks_user_id"), "prayer_bookmarks", ["user_id"], unique=False)

    op.create_table(
        "prayer_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prayer_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("user_name", sa.String(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=False),
        sa.Column("is_pastor_response", sa.Boolean(), nullable=True),
        sa.Column("is_pinned", sa.Boolean(), nullable=True),
        sa.Column("is_hidden", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["parent_id"], ["prayer_comments.id"]),
        sa.ForeignKeyConstraint(["prayer_id"], ["prayers.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_prayer_comments_created_at"), "prayer_comments", ["created_at"], unique=False)
    op.create_index(op.f("ix_prayer_comments_id"), "prayer_comments", ["id"], unique=False)
    op.create_index(op.f("ix_prayer_comments_prayer_id"), "prayer_comments", ["prayer_id"], unique=False)
    op.create_index(op.f("ix_prayer_comments_user_id"), "prayer_comments", ["user_id"], unique=False)

    op.create_table(
        "prayer_notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("prayer_id", sa.Integer(), nullable=True),
        sa.Column("notification_type", sa.String(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["prayer_id"], ["prayers.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_prayer_notifications_created_at"), "prayer_notifications", ["created_at"], unique=False)
    op.create_index(op.f("ix_prayer_notifications_id"), "prayer_notifications", ["id"], unique=False)
    op.create_index(op.f("ix_prayer_notifications_prayer_id"), "prayer_notifications", ["prayer_id"], unique=False)
    op.create_index(op.f("ix_prayer_notifications_user_id"), "prayer_notifications", ["user_id"], unique=False)

    op.create_table(
        "prayer_reactions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prayer_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reaction_type", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["prayer_id"], ["prayers.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "prayer_id",
            "user_id",
            "reaction_type",
            name="uq_prayer_user_reaction"
        ),
    )

    op.create_index(op.f("ix_prayer_reactions_id"), "prayer_reactions", ["id"], unique=False)
    op.create_index(op.f("ix_prayer_reactions_prayer_id"), "prayer_reactions", ["prayer_id"], unique=False)
    op.create_index(op.f("ix_prayer_reactions_user_id"), "prayer_reactions", ["user_id"], unique=False)

    op.create_table(
        "prayer_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("prayer_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["prayer_id"], ["prayers.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(op.f("ix_prayer_reports_id"), "prayer_reports", ["id"], unique=False)
    op.create_index(op.f("ix_prayer_reports_prayer_id"), "prayer_reports", ["prayer_id"], unique=False)
    op.create_index(op.f("ix_prayer_reports_user_id"), "prayer_reports", ["user_id"], unique=False)

    # =========================
    # PRAYERS TABLE UPGRADES
    # =========================
    op.add_column("prayers", sa.Column("category", sa.String(), nullable=True))
    op.add_column("prayers", sa.Column("status", sa.String(), nullable=True))
    op.add_column("prayers", sa.Column("is_anonymous", sa.Boolean(), nullable=True))
    op.add_column("prayers", sa.Column("is_hidden", sa.Boolean(), nullable=True))
    op.add_column("prayers", sa.Column("is_locked", sa.Boolean(), nullable=True))
    op.add_column("prayers", sa.Column("prayer_count", sa.Integer(), nullable=True))
    op.add_column("prayers", sa.Column("support_count", sa.Integer(), nullable=True))
    op.add_column("prayers", sa.Column("comment_count", sa.Integer(), nullable=True))
    op.add_column("prayers", sa.Column("share_count", sa.Integer(), nullable=True))
    op.add_column("prayers", sa.Column("answered_at", sa.DateTime(), nullable=True))
    op.add_column("prayers", sa.Column("updated_at", sa.DateTime(), nullable=True))

    # =========================
    # SAFE BACKFILL FOR EXISTING PRAYERS
    # =========================
    op.execute(
        """
        UPDATE prayers
        SET
            status = COALESCE(status, 'still_praying'),
            is_anonymous = COALESCE(is_anonymous, false),
            is_hidden = COALESCE(is_hidden, false),
            is_locked = COALESCE(is_locked, false),
            prayer_count = COALESCE(prayer_count, 0),
            support_count = COALESCE(support_count, 0),
            comment_count = COALESCE(comment_count, 0),
            share_count = COALESCE(share_count, 0),
            updated_at = COALESCE(updated_at, created_at)
        """
    )

    op.create_index(op.f("ix_prayers_category"), "prayers", ["category"], unique=False)
    op.create_index(op.f("ix_prayers_is_hidden"), "prayers", ["is_hidden"], unique=False)
    op.create_index(op.f("ix_prayers_status"), "prayers", ["status"], unique=False)
    op.create_index(op.f("ix_prayers_user_id"), "prayers", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(op.f("ix_prayers_user_id"), table_name="prayers")
    op.drop_index(op.f("ix_prayers_status"), table_name="prayers")
    op.drop_index(op.f("ix_prayers_is_hidden"), table_name="prayers")
    op.drop_index(op.f("ix_prayers_category"), table_name="prayers")

    op.drop_column("prayers", "updated_at")
    op.drop_column("prayers", "answered_at")
    op.drop_column("prayers", "share_count")
    op.drop_column("prayers", "comment_count")
    op.drop_column("prayers", "support_count")
    op.drop_column("prayers", "prayer_count")
    op.drop_column("prayers", "is_locked")
    op.drop_column("prayers", "is_hidden")
    op.drop_column("prayers", "is_anonymous")
    op.drop_column("prayers", "status")
    op.drop_column("prayers", "category")

    op.drop_index(op.f("ix_prayer_reports_user_id"), table_name="prayer_reports")
    op.drop_index(op.f("ix_prayer_reports_prayer_id"), table_name="prayer_reports")
    op.drop_index(op.f("ix_prayer_reports_id"), table_name="prayer_reports")
    op.drop_table("prayer_reports")

    op.drop_index(op.f("ix_prayer_reactions_user_id"), table_name="prayer_reactions")
    op.drop_index(op.f("ix_prayer_reactions_prayer_id"), table_name="prayer_reactions")
    op.drop_index(op.f("ix_prayer_reactions_id"), table_name="prayer_reactions")
    op.drop_table("prayer_reactions")

    op.drop_index(op.f("ix_prayer_notifications_user_id"), table_name="prayer_notifications")
    op.drop_index(op.f("ix_prayer_notifications_prayer_id"), table_name="prayer_notifications")
    op.drop_index(op.f("ix_prayer_notifications_id"), table_name="prayer_notifications")
    op.drop_index(op.f("ix_prayer_notifications_created_at"), table_name="prayer_notifications")
    op.drop_table("prayer_notifications")

    op.drop_index(op.f("ix_prayer_comments_user_id"), table_name="prayer_comments")
    op.drop_index(op.f("ix_prayer_comments_prayer_id"), table_name="prayer_comments")
    op.drop_index(op.f("ix_prayer_comments_id"), table_name="prayer_comments")
    op.drop_index(op.f("ix_prayer_comments_created_at"), table_name="prayer_comments")
    op.drop_table("prayer_comments")

    op.drop_index(op.f("ix_prayer_bookmarks_user_id"), table_name="prayer_bookmarks")
    op.drop_index(op.f("ix_prayer_bookmarks_prayer_id"), table_name="prayer_bookmarks")
    op.drop_index(op.f("ix_prayer_bookmarks_id"), table_name="prayer_bookmarks")
    op.drop_table("prayer_bookmarks")