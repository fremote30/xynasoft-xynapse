"""add immutable XynAssist AI execution ledger

Revision ID: 0008_xynassist
Revises: 0007_xynassist
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_xynassist"
down_revision = "0007_xynassist"
branch_labels = None
depends_on = None


TABLE_NAME = "xynassist_ai_executions"


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
            "request_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "operation",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(length=80),
            nullable=False,
        ),
        sa.Column(
            "model",
            sa.String(length=150),
            nullable=False,
        ),
        sa.Column(
            "input_tokens",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "output_tokens",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "attempt_number",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_xynassist_ai_executions",
        ),
    )

    for column in (
        "product",
        "external_user_id",
        "request_id",
        "operation",
        "provider",
        "model",
    ):
        op.create_index(
            f"ix_{TABLE_NAME}_{column}",
            TABLE_NAME,
            [column],
            unique=False,
        )


def downgrade():
    for column in reversed(
        (
            "product",
            "external_user_id",
            "request_id",
            "operation",
            "provider",
            "model",
        )
    ):
        op.drop_index(
            f"ix_{TABLE_NAME}_{column}",
            table_name=TABLE_NAME,
        )

    op.drop_table(TABLE_NAME)
