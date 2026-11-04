"""create jobs table

Revision ID: 42d472797760
Revises: 0005_store_file_blobs
Create Date: 2026-02-04 11:04:09.233004

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '42d472797760'
down_revision: Union[str, Sequence[str], None] = '0005_store_file_blobs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
