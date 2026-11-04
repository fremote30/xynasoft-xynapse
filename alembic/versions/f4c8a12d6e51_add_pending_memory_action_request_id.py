"""
add stable pending memory action request id

Revision ID: f4c8a12d6e51
Revises: f3a9c7d21b40
"""

from alembic import op
import sqlalchemy as sa


revision = "f4c8a12d6e51"
down_revision = "f3a9c7d21b40"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "conversation_pending_memory_actions",
        sa.Column(
            "action_request_id",
            sa.String(length=36),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_column(
        "conversation_pending_memory_actions",
        "action_request_id",
    )
