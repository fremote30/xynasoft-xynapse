"""add user name to prayers

Revision ID: b4eff2c1fec7
Revises: aec7c283bd1f
Create Date: 2026-07-20 21:05:22.838517

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4eff2c1fec7'
down_revision: Union[str, Sequence[str], None] = 'aec7c283bd1f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("prayers")
    }

    if "user_name" not in columns:
        # Add as nullable first because production may already contain prayers.
        op.add_column(
            "prayers",
            sa.Column("user_name", sa.String(), nullable=True),
        )

        # Use the associated user's name where possible.
        # Fall back to a safe display name for historical records.
        op.execute(
            """
            UPDATE prayers AS p
            SET user_name = COALESCE(
                NULLIF(TRIM(u.name), ''),
                NULLIF(TRIM(u.email), ''),
                'XynaFaith Member'
            )
            FROM users AS u
            WHERE p.user_id = u.id
              AND p.user_name IS NULL
            """
        )

        op.execute(
            """
            UPDATE prayers
            SET user_name = 'XynaFaith Member'
            WHERE user_name IS NULL
            """
        )

        op.alter_column(
            "prayers",
            "user_name",
            existing_type=sa.String(),
            nullable=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("prayers")
    }

    if "user_name" in columns:
        op.drop_column("prayers", "user_name")
