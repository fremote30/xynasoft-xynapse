"""add persistent XynAssist memory foundation

Revision ID: 0005_xynassist
Revises: 0004_xynassist
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_xynassist"
down_revision = "0004_xynassist"
branch_labels = None
depends_on = None


TABLE_NAME = "xynassist_memories"


def upgrade():
    op.create_table(
        TABLE_NAME,
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
            "memory_type",
            sa.String(length=80),
            nullable=False,
        ),
        sa.Column(
            "key",
            sa.String(length=160),
            nullable=False,
        ),
        sa.Column(
            "value",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "source",
            sa.String(length=80),
            nullable=False,
            server_default="explicit_user",
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
        sa.Column(
            "last_used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_xynassist_memories",
        ),
        sa.UniqueConstraint(
            "product",
            "external_user_id",
            "memory_type",
            "key",
            name="uq_xynassist_memory_owner_type_key",
        ),
    )

    for column in (
        "product",
        "external_user_id",
        "memory_type",
        "source",
        "status",
    ):
        op.create_index(
            f"ix_xynassist_memories_{column}",
            TABLE_NAME,
            [column],
        )


def downgrade():
    for column in reversed(
        (
            "product",
            "external_user_id",
            "memory_type",
            "source",
            "status",
        )
    ):
        op.drop_index(
            f"ix_xynassist_memories_{column}",
            table_name=TABLE_NAME,
        )

    op.drop_table(TABLE_NAME)
