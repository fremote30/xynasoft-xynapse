"""add V2 prayer testimony moderation

Revision ID: c8e3d01
Revises: b7d2c01
"""

from alembic import op
import sqlalchemy as sa


revision = "c8e3d01"
down_revision = "b7d2c01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "prayers",
        sa.Column(
            "testimony_status",
            sa.String(length=32),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_prayers_testimony_status",
        "prayers",
        ["testimony_status"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_prayers_testimony_status",
        table_name="prayers",
    )

    op.drop_column(
        "prayers",
        "testimony_status",
    )
