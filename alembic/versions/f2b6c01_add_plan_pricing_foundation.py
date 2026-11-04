"""add plan pricing foundation

Revision ID: f2b6c01
Revises: e1a5b01
"""

from alembic import op
import sqlalchemy as sa


revision = "f2b6c01"
down_revision = "e1a5b01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "plan_prices",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
        ),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey(
                "plans.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),
        sa.Column(
            "market_code",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
        ),
        sa.Column(
            "billing_interval",
            sa.String(length=16),
            nullable=False,
        ),
        sa.Column(
            "amount_minor",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "effective_from",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "effective_until",
            sa.DateTime(),
            nullable=True,
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
            "amount_minor >= 0",
            name="ck_plan_prices_amount_nonnegative",
        ),
        sa.CheckConstraint(
            "billing_interval IN ('monthly', 'annual')",
            name="ck_plan_prices_billing_interval",
        ),
        sa.CheckConstraint(
            "effective_until IS NULL OR effective_until > effective_from",
            name="ck_plan_prices_valid_effective_period",
        ),
    )

    op.create_index(
        "ix_plan_prices_plan_id",
        "plan_prices",
        ["plan_id"],
        unique=False,
    )

    op.create_index(
        "ix_plan_prices_market_code",
        "plan_prices",
        ["market_code"],
        unique=False,
    )

    op.create_index(
        "ix_plan_prices_plan_market_active",
        "plan_prices",
        [
            "plan_id",
            "market_code",
            "is_active",
        ],
        unique=False,
    )

    op.create_index(
        "ix_plan_prices_market_currency",
        "plan_prices",
        [
            "market_code",
            "currency",
        ],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_plan_prices_market_currency",
        table_name="plan_prices",
    )

    op.drop_index(
        "ix_plan_prices_plan_market_active",
        table_name="plan_prices",
    )

    op.drop_index(
        "ix_plan_prices_market_code",
        table_name="plan_prices",
    )

    op.drop_index(
        "ix_plan_prices_plan_id",
        table_name="plan_prices",
    )

    op.drop_table("plan_prices")
