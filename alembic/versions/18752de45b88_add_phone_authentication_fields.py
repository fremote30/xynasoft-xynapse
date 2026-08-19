"""add phone authentication fields

Revision ID: 18752de45b88
Revises: 148642f888fb
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "18752de45b88"
down_revision: Union[str, Sequence[str], None] = "148642f888fb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:

    op.add_column(
        "users",
        sa.Column(
            "phone",
            sa.String(length=32),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "phone_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "auth_method",
            sa.String(length=20),
            nullable=False,
            server_default="email",
        ),
    )

    op.create_index(
        "ix_users_phone",
        "users",
        ["phone"],
        unique=True,
    )


def downgrade() -> None:

    op.drop_index(
        "ix_users_phone",
        table_name="users",
    )

    op.drop_column(
        "users",
        "auth_method",
    )

    op.drop_column(
        "users",
        "phone_verified",
    )

    op.drop_column(
        "users",
        "phone",
    )
