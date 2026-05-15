"""merge heads 0006 and 42d

Revision ID: c32676206d78
Revises: 0006_create_jobs, 42d472797760
Create Date: 2026-02-12 06:58:00.295009

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c32676206d78'
down_revision: Union[str, Sequence[str], None] = ('0006_create_jobs', '42d472797760')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
