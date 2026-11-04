"""add church metadata fields

Revision ID: 510c2647a34e
Revises: c3c8333e8634
Create Date: 2026-07-19 09:03:44.498610
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "510c2647a34e"
down_revision: Union[str, Sequence[str], None] = "c3c8333e8634"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "churches",
        "name",
        existing_type=sa.String(),
        nullable=False,
    )

    op.add_column(
        "churches",
        sa.Column("denomination", sa.String(), nullable=True),
    )
    op.add_column(
        "churches",
        sa.Column("country", sa.String(), nullable=True),
    )
    op.add_column(
        "churches",
        sa.Column("city", sa.String(), nullable=True),
    )
    op.add_column(
        "churches",
        sa.Column("is_featured", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "churches",
        sa.Column("is_verified", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("churches", "is_verified")
    op.drop_column("churches", "is_featured")
    op.drop_column("churches", "city")
    op.drop_column("churches", "country")
    op.drop_column("churches", "denomination")

    op.alter_column(
        "churches",
        "name",
        existing_type=sa.String(),
        nullable=True,
    )