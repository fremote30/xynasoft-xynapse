"""add conversation pending actions

Revision ID: 6g6c5a
Revises: 6g6a01
Create Date: 2026-09-04
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "6g6c5a"
down_revision: Union[
    str,
    Sequence[str],
    None,
] = "6g6a01"
branch_labels: Union[
    str,
    Sequence[str],
    None,
] = None
depends_on: Union[
    str,
    Sequence[str],
    None,
] = None


def upgrade() -> None:
    op.create_table(
        "conversation_pending_actions",

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
            "resource_type",
            sa.String(length=150),
            nullable=False,
        ),

        sa.Column(
            "resource_id",
            sa.Integer(),
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
            server_default=sa.text("now()"),
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
                "uq_conversation_pending_action_"
                "user_conversation"
            ),
        ),
    )

    op.create_index(
        "ix_conversation_pending_actions_id",
        "conversation_pending_actions",
        ["id"],
        unique=False,
    )

    op.create_index(
        "ix_conversation_pending_actions_user_id",
        "conversation_pending_actions",
        ["user_id"],
        unique=False,
    )

    op.create_index(
        "ix_conversation_pending_actions_conversation_id",
        "conversation_pending_actions",
        ["conversation_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversation_pending_actions_conversation_id",
        table_name="conversation_pending_actions",
    )

    op.drop_index(
        "ix_conversation_pending_actions_user_id",
        table_name="conversation_pending_actions",
    )

    op.drop_index(
        "ix_conversation_pending_actions_id",
        table_name="conversation_pending_actions",
    )

    op.drop_table(
        "conversation_pending_actions"
    )
