"""add v2 monetization foundation

Revision ID: d1e4b7c9a2f1
Revises: bcc34996e4f3
"""

from alembic import op
import sqlalchemy as sa


revision = "d1e4b7c9a2f1"
down_revision = "bcc34996e4f3"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("access_profile", sa.String(length=64), nullable=False),
        sa.Column("owner_type", sa.String(length=32), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
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
        sa.UniqueConstraint("code", name="uq_plans_code"),
    )
    op.create_index("ix_plans_code", "plans", ["code"], unique=False)

    op.create_table(
        "plan_entitlements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entitlement_key", sa.String(length=120), nullable=False),
        sa.Column(
            "enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("usage_period", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "plan_id",
            "entitlement_key",
            name="uq_plan_entitlements_plan_key",
        ),
    )
    op.create_index(
        "ix_plan_entitlements_plan_id",
        "plan_entitlements",
        ["plan_id"],
        unique=False,
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("plans.id"),
            nullable=False,
        ),
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
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "starts_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("current_period_start", sa.DateTime(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(), nullable=True),
        sa.Column("canceled_at", sa.DateTime(), nullable=True),
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
            name="ck_subscriptions_exactly_one_owner",
        ),
    )
    op.create_index(
        "ix_subscriptions_plan_id",
        "subscriptions",
        ["plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscriptions_user_id",
        "subscriptions",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscriptions_church_id",
        "subscriptions",
        ["church_id"],
        unique=False,
    )

    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("request_id", sa.String(length=128), nullable=False),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "church_id",
            sa.Integer(),
            sa.ForeignKey("churches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "subscription_id",
            sa.Integer(),
            sa.ForeignKey("subscriptions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("entitlement_key", sa.String(length=120), nullable=False),
        sa.Column("metric", sa.String(length=64), nullable=False),
        sa.Column(
            "units",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "request_id",
            name="uq_ai_usage_events_request_id",
        ),
    )

    op.create_index(
        "ix_ai_usage_events_request_id",
        "ai_usage_events",
        ["request_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_usage_events_user_id",
        "ai_usage_events",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_usage_events_church_id",
        "ai_usage_events",
        ["church_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_usage_events_subscription_id",
        "ai_usage_events",
        ["subscription_id"],
        unique=False,
    )
    op.create_index(
        "ix_ai_usage_events_entitlement_key",
        "ai_usage_events",
        ["entitlement_key"],
        unique=False,
    )
    op.create_index(
        "ix_ai_usage_events_metric",
        "ai_usage_events",
        ["metric"],
        unique=False,
    )
    op.create_index(
        "ix_ai_usage_events_created_at",
        "ai_usage_events",
        ["created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_ai_usage_events_created_at",
        table_name="ai_usage_events",
    )
    op.drop_index(
        "ix_ai_usage_events_metric",
        table_name="ai_usage_events",
    )
    op.drop_index(
        "ix_ai_usage_events_entitlement_key",
        table_name="ai_usage_events",
    )
    op.drop_index(
        "ix_ai_usage_events_subscription_id",
        table_name="ai_usage_events",
    )
    op.drop_index(
        "ix_ai_usage_events_church_id",
        table_name="ai_usage_events",
    )
    op.drop_index(
        "ix_ai_usage_events_user_id",
        table_name="ai_usage_events",
    )
    op.drop_index(
        "ix_ai_usage_events_request_id",
        table_name="ai_usage_events",
    )
    op.drop_table("ai_usage_events")

    op.drop_index(
        "ix_subscriptions_church_id",
        table_name="subscriptions",
    )
    op.drop_index(
        "ix_subscriptions_user_id",
        table_name="subscriptions",
    )
    op.drop_index(
        "ix_subscriptions_plan_id",
        table_name="subscriptions",
    )
    op.drop_table("subscriptions")

    op.drop_index(
        "ix_plan_entitlements_plan_id",
        table_name="plan_entitlements",
    )
    op.drop_table("plan_entitlements")

    op.drop_index(
        "ix_plans_code",
        table_name="plans",
    )
    op.drop_table("plans")
