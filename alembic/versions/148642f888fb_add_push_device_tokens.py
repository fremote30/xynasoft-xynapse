"""add push device tokens

Revision ID: 148642f888fb
Revises: b4eff2c1fec7
Create Date: 2026-08-17 04:49:55.276382
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "148642f888fb"
down_revision: Union[str, Sequence[str], None] = "b4eff2c1fec7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "push_device_tokens",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),

        sa.Column(
            "token",
            sa.String(),
            nullable=False,
        ),

        sa.Column(
            "platform",
            sa.String(length=20),
            nullable=False,
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),

        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "token",
            name="uq_push_device_tokens_token",
        ),
    )

    op.create_index(
        "ix_push_device_tokens_id",
        "push_device_tokens",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_push_device_tokens_user_id",
        "push_device_tokens",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_push_device_tokens_token",
        "push_device_tokens",
        ["token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_push_device_tokens_token",
        table_name="push_device_tokens",
    )

    op.drop_index(
        "ix_push_device_tokens_user_id",
        table_name="push_device_tokens",
    )

    op.drop_index(
        "ix_push_device_tokens_id",
        table_name="push_device_tokens",
    )

    op.drop_table("push_device_tokens")
