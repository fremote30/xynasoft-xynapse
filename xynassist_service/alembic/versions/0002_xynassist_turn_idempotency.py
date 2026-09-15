"""add XynAssist turn idempotency

Revision ID: 0002_xynassist
Revises: 0001_xynassist
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_xynassist"
down_revision = "0001_xynassist"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "xynassist_conversation_turns",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "product",
            sa.String(length=80),
            nullable=False,
        ),
        sa.Column(
            "external_user_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "request_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "request_fingerprint",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "user_message_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "assistant_message_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "response_json",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "error_code",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["xynassist_conversations.id"],
            name=(
                "fk_xynassist_turn_"
                "conversation"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_message_id"],
            [
                "xynassist_conversation_messages.id"
            ],
            name=(
                "fk_xynassist_turn_"
                "user_message"
            ),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["assistant_message_id"],
            [
                "xynassist_conversation_messages.id"
            ],
            name=(
                "fk_xynassist_turn_"
                "assistant_message"
            ),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=(
                "pk_xynassist_"
                "conversation_turns"
            ),
        ),
        sa.UniqueConstraint(
            "product",
            "external_user_id",
            "request_id",
            name=(
                "uq_xynassist_turn_"
                "product_user_request"
            ),
        ),
    )

    op.create_index(
        "ix_xynassist_conversation_turns_product",
        "xynassist_conversation_turns",
        ["product"],
    )

    op.create_index(
        (
            "ix_xynassist_conversation_turns_"
            "external_user_id"
        ),
        "xynassist_conversation_turns",
        ["external_user_id"],
    )

    op.create_index(
        (
            "ix_xynassist_conversation_turns_"
            "conversation_id"
        ),
        "xynassist_conversation_turns",
        ["conversation_id"],
    )

    op.create_index(
        (
            "ix_xynassist_conversation_turns_"
            "request_id"
        ),
        "xynassist_conversation_turns",
        ["request_id"],
    )

    op.create_index(
        "ix_xynassist_conversation_turns_status",
        "xynassist_conversation_turns",
        ["status"],
    )


def downgrade():
    op.drop_index(
        "ix_xynassist_conversation_turns_status",
        table_name="xynassist_conversation_turns",
    )

    op.drop_index(
        (
            "ix_xynassist_conversation_turns_"
            "request_id"
        ),
        table_name="xynassist_conversation_turns",
    )

    op.drop_index(
        (
            "ix_xynassist_conversation_turns_"
            "conversation_id"
        ),
        table_name="xynassist_conversation_turns",
    )

    op.drop_index(
        (
            "ix_xynassist_conversation_turns_"
            "external_user_id"
        ),
        table_name="xynassist_conversation_turns",
    )

    op.drop_index(
        (
            "ix_xynassist_conversation_turns_"
            "product"
        ),
        table_name="xynassist_conversation_turns",
    )

    op.drop_table(
        "xynassist_conversation_turns"
    )
