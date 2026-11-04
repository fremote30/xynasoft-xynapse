"""add group targeting to church content

Revision ID: h4d8e01
Revises: g3c7d01
"""

from alembic import op
import sqlalchemy as sa


revision = "h4d8e01"
down_revision = "g3c7d01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "church_announcements",
        sa.Column("target_group_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_church_announcements_target_group_id",
        "church_announcements",
        "church_groups",
        ["target_group_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_church_announcements_target_group_id",
        "church_announcements",
        ["target_group_id"],
        unique=False,
    )

    op.add_column(
        "church_events",
        sa.Column("target_group_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_church_events_target_group_id",
        "church_events",
        "church_groups",
        ["target_group_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_church_events_target_group_id",
        "church_events",
        ["target_group_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_church_events_target_group_id",
        table_name="church_events",
    )
    op.drop_constraint(
        "fk_church_events_target_group_id",
        "church_events",
        type_="foreignkey",
    )
    op.drop_column("church_events", "target_group_id")

    op.drop_index(
        "ix_church_announcements_target_group_id",
        table_name="church_announcements",
    )
    op.drop_constraint(
        "fk_church_announcements_target_group_id",
        "church_announcements",
        type_="foreignkey",
    )
    op.drop_column("church_announcements", "target_group_id")
