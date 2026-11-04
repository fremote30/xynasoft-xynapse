"""merge 0003 heads

Revision ID: 0004_merge_heads
Revises: 0003_blobs, 0003_files
Create Date: 2026-02-02 06:22:34.883949

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0004_merge_heads'
down_revision: Union[str, Sequence[str], None] = ('0003_blobs', '0003_files')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
