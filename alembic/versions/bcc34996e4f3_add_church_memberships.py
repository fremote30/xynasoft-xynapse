"""add church memberships

Revision ID: bcc34996e4f3
Revises: 6g6c5a
Create Date: 2026-09-13 07:14:54.372586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bcc34996e4f3'
down_revision: Union[str, Sequence[str], None] = '6g6c5a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "church_memberships",
        sa.Column("id", sa.Integer(), nullable=False),

        sa.Column(
            "church_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "role",
            sa.String(length=32),
            nullable=False,
            server_default="member",
        ),

        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),

        sa.Column(
            "is_primary",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),

        sa.Column(
            "joined_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
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
            name="fk_church_memberships_church_id",
            ondelete="CASCADE",
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_church_memberships_user_id",
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint(
            "id",
            name="pk_church_memberships",
        ),

        sa.UniqueConstraint(
            "church_id",
            "user_id",
            name="uq_church_memberships_church_user",
        ),
    )

    op.create_index(
        "ix_church_memberships_church_id",
        "church_memberships",
        ["church_id"],
        unique=False,
    )

    op.create_index(
        "ix_church_memberships_user_id",
        "church_memberships",
        ["user_id"],
        unique=False,
    )

    # A user may belong to multiple churches, but only one membership
    # may be designated as the user's primary Church Space.
    op.create_index(
        "uq_church_memberships_primary_user",
        "church_memberships",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("is_primary = true"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_church_memberships_primary_user",
        table_name="church_memberships",
    )

    op.drop_index(
        "ix_church_memberships_user_id",
        table_name="church_memberships",
    )

    op.drop_index(
        "ix_church_memberships_church_id",
        table_name="church_memberships",
    )

    op.drop_table("church_memberships")
