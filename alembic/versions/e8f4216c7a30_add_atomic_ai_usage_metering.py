"""add atomic ai usage metering

Revision ID: e8f4216c7a30
Revises: d1e4b7c9a2f1
"""

from alembic import op
import sqlalchemy as sa


revision = "e8f4216c7a30"
down_revision = "d1e4b7c9a2f1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "usage_buckets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "church_id",
            sa.Integer(),
            sa.ForeignKey("churches.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "entitlement_key",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "metric",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "period_start",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "period_end",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "allowance_units",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "consumed_units",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "reserved_units",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            """
            (
                user_id IS NOT NULL
                AND church_id IS NULL
            )
            OR
            (
                user_id IS NULL
                AND church_id IS NOT NULL
            )
            """,
            name="ck_usage_buckets_exactly_one_owner",
        ),
        sa.CheckConstraint(
            "consumed_units >= 0",
            name="ck_usage_buckets_consumed_nonnegative",
        ),
        sa.CheckConstraint(
            "reserved_units >= 0",
            name="ck_usage_buckets_reserved_nonnegative",
        ),
        sa.CheckConstraint(
            "allowance_units >= 0",
            name="ck_usage_buckets_allowance_nonnegative",
        ),
        sa.CheckConstraint(
            "period_end > period_start",
            name="ck_usage_buckets_valid_period",
        ),
    )

    op.create_index(
        "ix_usage_buckets_user_id",
        "usage_buckets",
        ["user_id"],
    )
    op.create_index(
        "ix_usage_buckets_church_id",
        "usage_buckets",
        ["church_id"],
    )
    op.create_index(
        "ix_usage_buckets_entitlement_key",
        "usage_buckets",
        ["entitlement_key"],
    )
    op.create_index(
        "ix_usage_buckets_metric",
        "usage_buckets",
        ["metric"],
    )
    op.create_index(
        "ix_usage_buckets_period_start",
        "usage_buckets",
        ["period_start"],
    )

    op.create_index(
        "uq_usage_buckets_user_period",
        "usage_buckets",
        [
            "user_id",
            "entitlement_key",
            "metric",
            "period_start",
        ],
        unique=True,
        postgresql_where=sa.text("user_id IS NOT NULL"),
    )

    op.create_index(
        "uq_usage_buckets_church_period",
        "usage_buckets",
        [
            "church_id",
            "entitlement_key",
            "metric",
            "period_start",
        ],
        unique=True,
        postgresql_where=sa.text("church_id IS NOT NULL"),
    )

    op.create_table(
        "ai_usage_reservations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "request_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "bucket_id",
            sa.Integer(),
            sa.ForeignKey(
                "usage_buckets.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey(
                "users.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "church_id",
            sa.Integer(),
            sa.ForeignKey(
                "churches.id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        sa.Column(
            "subscription_id",
            sa.Integer(),
            sa.ForeignKey(
                "subscriptions.id",
                ondelete="SET NULL",
            ),
            nullable=True,
        ),
        sa.Column(
            "entitlement_key",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "metric",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "units",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="reserved",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.Column(
            "released_at",
            sa.DateTime(),
            nullable=True,
        ),
        sa.CheckConstraint(
            "units > 0",
            name="ck_ai_usage_reservations_positive_units",
        ),
        sa.UniqueConstraint(
            "request_id",
            name="uq_ai_usage_reservations_request_id",
        ),
    )

    for column in (
        "request_id",
        "bucket_id",
        "user_id",
        "church_id",
        "subscription_id",
        "entitlement_key",
        "metric",
        "status",
    ):
        op.create_index(
            f"ix_ai_usage_reservations_{column}",
            "ai_usage_reservations",
            [column],
        )


def downgrade():
    for column in (
        "status",
        "metric",
        "entitlement_key",
        "subscription_id",
        "church_id",
        "user_id",
        "bucket_id",
        "request_id",
    ):
        op.drop_index(
            f"ix_ai_usage_reservations_{column}",
            table_name="ai_usage_reservations",
        )

    op.drop_table("ai_usage_reservations")

    op.drop_index(
        "uq_usage_buckets_church_period",
        table_name="usage_buckets",
    )
    op.drop_index(
        "uq_usage_buckets_user_period",
        table_name="usage_buckets",
    )
    op.drop_index(
        "ix_usage_buckets_period_start",
        table_name="usage_buckets",
    )
    op.drop_index(
        "ix_usage_buckets_metric",
        table_name="usage_buckets",
    )
    op.drop_index(
        "ix_usage_buckets_entitlement_key",
        table_name="usage_buckets",
    )
    op.drop_index(
        "ix_usage_buckets_church_id",
        table_name="usage_buckets",
    )
    op.drop_index(
        "ix_usage_buckets_user_id",
        table_name="usage_buckets",
    )

    op.drop_table("usage_buckets")
