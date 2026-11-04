"""church groups and ministries foundation

Revision ID: g3c7d01
Revises: f2b6c01
"""

from alembic import op
import sqlalchemy as sa


revision = "g3c7d01"
down_revision = "f2b6c01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "church_groups",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("church_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("group_type", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["church_id"],
            ["churches.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "church_id",
            "name",
            name="uq_church_groups_church_name",
        ),
    )

    op.create_index(
        op.f("ix_church_groups_church_id"),
        "church_groups",
        ["church_id"],
        unique=False,
    )

    op.create_table(
        "church_group_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("church_membership_id", sa.Integer(), nullable=False),
        sa.Column(
            "role",
            sa.String(length=32),
            server_default="member",
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="active",
            nullable=False,
        ),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["church_groups.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["church_membership_id"],
            ["church_memberships.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "group_id",
            "church_membership_id",
            name="uq_church_group_memberships_group_membership",
        ),
    )

    op.create_index(
        op.f("ix_church_group_memberships_group_id"),
        "church_group_memberships",
        ["group_id"],
        unique=False,
    )

    op.create_index(
        op.f("ix_church_group_memberships_church_membership_id"),
        "church_group_memberships",
        ["church_membership_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f("ix_church_group_memberships_church_membership_id"),
        table_name="church_group_memberships",
    )
    op.drop_index(
        op.f("ix_church_group_memberships_group_id"),
        table_name="church_group_memberships",
    )
    op.drop_table("church_group_memberships")

    op.drop_index(
        op.f("ix_church_groups_church_id"),
        table_name="church_groups",
    )
    op.drop_table("church_groups")
