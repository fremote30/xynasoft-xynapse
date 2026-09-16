"""add durable XynAssist action executions

Revision ID: 0006_xynassist
Revises: 0005_xynassist
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_xynassist"
down_revision = "0005_xynassist"
branch_labels = None
depends_on = None


TABLE_NAME = "xynassist_action_executions"


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
            "action_name",
            sa.String(length=150),
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
            "result_json",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_xynassist_action_executions",
        ),
        sa.UniqueConstraint(
            "product",
            "external_user_id",
            "request_id",
            name=(
                "uq_xynassist_action_execution_"
                "product_user_request"
            ),
        ),
    )

    for column in (
        "product",
        "external_user_id",
        "request_id",
        "action_name",
        "status",
    ):
        op.create_index(
            (
                "ix_xynassist_action_executions_"
                f"{column}"
            ),
            TABLE_NAME,
            [column],
        )


def downgrade():
    for column in reversed(
        (
            "product",
            "external_user_id",
            "request_id",
            "action_name",
            "status",
        )
    ):
        op.drop_index(
            (
                "ix_xynassist_action_executions_"
                f"{column}"
            ),
            table_name=TABLE_NAME,
        )

    op.drop_table(TABLE_NAME)
