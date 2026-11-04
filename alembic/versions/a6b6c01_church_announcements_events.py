"""add church announcements and events

Revision ID: a6b6c01
Revises: f4c8a12d6e51
"""

from alembic import op
import sqlalchemy as sa


revision = "a6b6c01"
down_revision = "f4c8a12d6e51"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "church_announcements",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "church_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "author_user_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "body",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "published_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["church_id"],
            ["churches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
    )

    op.create_index(
        "ix_church_announcements_church_status",
        "church_announcements",
        ["church_id", "status"],
    )

    op.create_index(
        "ix_church_announcements_church_published",
        "church_announcements",
        ["church_id", "published_at"],
    )

    op.create_table(
        "church_events",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "church_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "starts_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "ends_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "location",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "event_url",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "published_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["church_id"],
            ["churches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
    )

    op.create_index(
        "ix_church_events_church_status",
        "church_events",
        ["church_id", "status"],
    )

    op.create_index(
        "ix_church_events_church_starts",
        "church_events",
        ["church_id", "starts_at"],
    )


def downgrade():
    op.drop_index(
        "ix_church_events_church_starts",
        table_name="church_events",
    )
    op.drop_index(
        "ix_church_events_church_status",
        table_name="church_events",
    )
    op.drop_table("church_events")

    op.drop_index(
        "ix_church_announcements_church_published",
        table_name="church_announcements",
    )
    op.drop_index(
        "ix_church_announcements_church_status",
        table_name="church_announcements",
    )
    op.drop_table("church_announcements")
