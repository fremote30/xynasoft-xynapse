"""create XynAssist conversation foundation

Revision ID: 0001_xynassist
Revises:
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_xynassist"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "xynassist_conversations",
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
            "title",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "status",
            sa.String(length=40),
            nullable=False,
            server_default="active",
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
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_xynassist_conversations",
        ),
        sa.UniqueConstraint(
            "product",
            "external_user_id",
            "id",
            name=(
                "uq_xynassist_conversation_"
                "product_user_id"
            ),
        ),
    )

    op.create_index(
        "ix_xynassist_conversations_product",
        "xynassist_conversations",
        ["product"],
    )

    op.create_index(
        "ix_xynassist_conversations_external_user_id",
        "xynassist_conversations",
        ["external_user_id"],
    )

    op.create_index(
        "ix_xynassist_conversations_status",
        "xynassist_conversations",
        ["status"],
    )

    op.create_table(
        "xynassist_conversation_messages",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=40),
            nullable=False,
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "skill",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"],
            ["xynassist_conversations.id"],
            name=(
                "fk_xynassist_messages_"
                "conversation"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name=(
                "pk_xynassist_"
                "conversation_messages"
            ),
        ),
    )

    op.create_index(
        "ix_xynassist_conversation_messages_conversation_id",
        "xynassist_conversation_messages",
        ["conversation_id"],
    )

    op.create_index(
        "ix_xynassist_conversation_messages_role",
        "xynassist_conversation_messages",
        ["role"],
    )

    op.create_index(
        "ix_xynassist_conversation_messages_skill",
        "xynassist_conversation_messages",
        ["skill"],
    )


def downgrade():
    op.drop_index(
        "ix_xynassist_conversation_messages_skill",
        table_name=(
            "xynassist_conversation_messages"
        ),
    )

    op.drop_index(
        "ix_xynassist_conversation_messages_role",
        table_name=(
            "xynassist_conversation_messages"
        ),
    )

    op.drop_index(
        (
            "ix_xynassist_conversation_messages_"
            "conversation_id"
        ),
        table_name=(
            "xynassist_conversation_messages"
        ),
    )

    op.drop_table(
        "xynassist_conversation_messages"
    )

    op.drop_index(
        "ix_xynassist_conversations_status",
        table_name="xynassist_conversations",
    )

    op.drop_index(
        (
            "ix_xynassist_conversations_"
            "external_user_id"
        ),
        table_name="xynassist_conversations",
    )

    op.drop_index(
        "ix_xynassist_conversations_product",
        table_name="xynassist_conversations",
    )

    op.drop_table(
        "xynassist_conversations"
    )
