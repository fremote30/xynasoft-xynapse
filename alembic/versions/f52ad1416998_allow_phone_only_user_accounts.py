"""allow phone only user accounts

Revision ID: f52ad1416998
Revises: 18752de45b88
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f52ad1416998"
down_revision: Union[str, Sequence[str], None] = "18752de45b88"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(),
        nullable=True,
    )

    op.alter_column(
        "users",
        "password",
        existing_type=sa.String(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "users",
        "password",
        existing_type=sa.String(),
        nullable=False,
    )

    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(),
        nullable=False,
    )
