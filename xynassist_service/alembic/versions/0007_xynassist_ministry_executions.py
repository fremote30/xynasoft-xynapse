"""add durable XynAssist ministry executions

Revision ID: 0007_xynassist
Revises: 0006_xynassist
"""

from alembic import op
import sqlalchemy as sa


revision = "0007_xynassist"
down_revision = "0006_xynassist"
branch_labels = None
depends_on = None


TABLE_NAME = "xynassist_ministry_executions"


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
            "skill",
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
            nullable=True,
        ),
        sa.Column(
            "error_code",
            sa.String(length=120),
            nullable=True,
        ),
        sa.Column(
            "lease_token",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "lease_expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "attempt_count",
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
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_xynassist_ministry_executions",
        ),
        sa.UniqueConstraint(
            "product",
            "external_user_id",
            "request_id",
            name=(
                "uq_xynassist_ministry_execution_"
                "product_user_request"
            ),
        ),
    )

    for column in (
        "product",
        "external_user_id",
        "request_id",
        "skill",
        "status",
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
            "skill",
            "status",
        )
    ):
        op.drop_index(
            f"ix_{TABLE_NAME}_{column}",
            table_name=TABLE_NAME,
        )

    op.drop_table(TABLE_NAME)
