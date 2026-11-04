"""extend pending actions for operational actions

Revision ID: j6f0g01
Revises: i5e9f01
"""

from alembic import op
import sqlalchemy as sa


revision = "j6f0g01"
down_revision = "i5e9f01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "conversation_pending_actions",
        sa.Column(
            "arguments",
            sa.JSON(),
            nullable=True,
        ),
    )
    op.add_column(
        "conversation_pending_actions",
        sa.Column(
            "action_request_id",
            sa.String(length=36),
            nullable=True,
        ),
    )
    op.add_column(
        "conversation_pending_actions",
        sa.Column(
            "church_id",
            sa.Integer(),
            nullable=True,
        ),
    )
    op.create_foreign_key(
        "fk_conversation_pending_actions_church_id_churches",
        "conversation_pending_actions",
        "churches",
        ["church_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_conversation_pending_actions_church_id",
        "conversation_pending_actions",
        ["church_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_conversation_pending_actions_church_id",
        table_name="conversation_pending_actions",
    )
    op.drop_constraint(
        "fk_conversation_pending_actions_church_id_churches",
        "conversation_pending_actions",
        type_="foreignkey",
    )
    op.drop_column(
        "conversation_pending_actions",
        "church_id",
    )
    op.drop_column(
        "conversation_pending_actions",
        "action_request_id",
    )
    op.drop_column(
        "conversation_pending_actions",
        "arguments",
    )
