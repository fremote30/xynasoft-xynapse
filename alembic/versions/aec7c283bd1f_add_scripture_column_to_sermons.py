"""add scripture column to sermons

Revision ID: aec7c283bd1f
Revises: 510c2647a34e
Create Date: 2026-07-20 20:31:55.671978

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision: str = 'aec7c283bd1f'
down_revision: Union[str, Sequence[str], None] = '510c2647a34e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    columns = [c["name"] for c in inspector.get_columns("sermons")]

    if "scripture" not in columns:
        op.add_column(
            "sermons",
            sa.Column(
                "scripture",
                sa.String(),
                nullable=True,
            ),
        )


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    columns = [c["name"] for c in inspector.get_columns("sermons")]

    if "scripture" in columns:
        op.drop_column("sermons", "scripture")