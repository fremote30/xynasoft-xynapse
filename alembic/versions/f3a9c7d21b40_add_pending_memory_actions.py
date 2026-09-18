"""
add pending conversational memory actions

Revision ID: f3a9c7d21b40
Revises: e8f4216c7a30
"""

from alembic import op
import sqlalchemy as sa


revision = "f3a9c7d21b40"
down_revision = "e8f4216c7a30"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "conversation_pending_memory_actions",
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
            "conversation_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "action_name",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "memory_type",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "memory_key",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "source_message_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "conversation_id",
            name=(
                "uq_conversation_pending_memory_action_"
                "user_conversation"
            ),
        ),
    )

    op.create_index(
        op.f(
            "ix_conversation_pending_memory_actions_id"
        ),
        "conversation_pending_memory_actions",
        ["id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_conversation_pending_memory_actions_user_id"
        ),
        "conversation_pending_memory_actions",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_conversation_pending_memory_actions_"
            "conversation_id"
        ),
        "conversation_pending_memory_actions",
        ["conversation_id"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        op.f(
            "ix_conversation_pending_memory_actions_"
            "conversation_id"
        ),
        table_name=(
            "conversation_pending_memory_actions"
        ),
    )

    op.drop_index(
        op.f(
            "ix_conversation_pending_memory_actions_user_id"
        ),
        table_name=(
            "conversation_pending_memory_actions"
        ),
    )

    op.drop_index(
        op.f(
            "ix_conversation_pending_memory_actions_id"
        ),
        table_name=(
            "conversation_pending_memory_actions"
        ),
    )

    op.drop_table(
        "conversation_pending_memory_actions"
    )
