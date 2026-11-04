"""add conversation action execution idempotency

Revision ID: 6g6a01
Revises: f52ad1416998
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "6g6a01"
down_revision = "f52ad1416998"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversation_action_executions",
        sa.Column(
            "id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "request_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "source_message_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "action_name",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "result",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "user_id",
            "request_id",
            name=(
                "uq_conversation_action_execution_"
                "user_request"
            ),
        ),
    )

    op.create_index(
        op.f(
            "ix_conversation_action_executions_id"
        ),
        "conversation_action_executions",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_conversation_action_executions_user_id"
        ),
        "conversation_action_executions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f(
            "ix_conversation_action_executions_user_id"
        ),
        table_name=(
            "conversation_action_executions"
        ),
    )

    op.drop_index(
        op.f(
            "ix_conversation_action_executions_id"
        ),
        table_name=(
            "conversation_action_executions"
        ),
    )

    op.drop_table(
        "conversation_action_executions"
    )
