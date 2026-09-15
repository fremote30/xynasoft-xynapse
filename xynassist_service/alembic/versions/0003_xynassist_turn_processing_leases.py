"""add XynAssist turn processing leases

Revision ID: 0003_xynassist
Revises: 0002_xynassist
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_xynassist"
down_revision = "0002_xynassist"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "xynassist_conversation_turns",
        sa.Column(
            "lease_token",
            sa.String(length=36),
            nullable=True,
        ),
    )

    op.add_column(
        "xynassist_conversation_turns",
        sa.Column(
            "lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.add_column(
        "xynassist_conversation_turns",
        sa.Column(
            "attempt_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )

    # Existing processing rows from 0002 have no lease metadata.
    # The service will treat those legacy rows as recoverable.
    op.create_index(
        "ix_xynassist_turn_processing_lease",
        "xynassist_conversation_turns",
        [
            "status",
            "lease_expires_at",
        ],
    )


def downgrade():
    op.drop_index(
        "ix_xynassist_turn_processing_lease",
        table_name="xynassist_conversation_turns",
    )

    op.drop_column(
        "xynassist_conversation_turns",
        "attempt_count",
    )

    op.drop_column(
        "xynassist_conversation_turns",
        "lease_expires_at",
    )

    op.drop_column(
        "xynassist_conversation_turns",
        "lease_token",
    )
