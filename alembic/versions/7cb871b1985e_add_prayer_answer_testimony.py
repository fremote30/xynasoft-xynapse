"""add prayer answer testimony

Revision ID: 7cb871b1985e
Revises: 283725dde09f
Create Date: 2026-07-08 11:19:34.000512
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7cb871b1985e"
down_revision: Union[str, Sequence[str], None] = "283725dde09f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "prayers",
        sa.Column(
            "answer_testimony",
            sa.Text(),
            nullable=True
        )
    )

    op.add_column(
        "prayers",
        sa.Column(
            "testimony_shared_at",
            sa.DateTime(),
            nullable=True
        )
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column(
        "prayers",
        "testimony_shared_at"
    )

    op.drop_column(
        "prayers",
        "answer_testimony"
    )