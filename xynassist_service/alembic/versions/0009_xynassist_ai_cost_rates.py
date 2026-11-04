"""add XynAssist AI cost rates

Revision ID: 0009_xynassist
Revises: 0008_xynassist
"""

from alembic import op
import sqlalchemy as sa


revision = "0009_xynassist"
down_revision = "0008_xynassist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "xynassist_ai_cost_rates",
        sa.Column(
            "id",
            sa.Integer(),
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
            "input_cost_per_million_micro_usd",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "output_cost_per_million_micro_usd",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "effective_from",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "effective_until",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "input_cost_per_million_micro_usd >= 0",
            name="ck_xynassist_ai_cost_rate_input_nonnegative",
        ),
        sa.CheckConstraint(
            "output_cost_per_million_micro_usd >= 0",
            name="ck_xynassist_ai_cost_rate_output_nonnegative",
        ),
        sa.CheckConstraint(
            "effective_until IS NULL OR "
            "effective_until > effective_from",
            name="ck_xynassist_ai_cost_rate_effective_period",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        op.f(
            "ix_xynassist_ai_cost_rates_provider"
        ),
        "xynassist_ai_cost_rates",
        ["provider"],
        unique=False,
    )

    op.create_index(
        op.f(
            "ix_xynassist_ai_cost_rates_model"
        ),
        "xynassist_ai_cost_rates",
        ["model"],
        unique=False,
    )

    op.create_index(
        "ix_xynassist_ai_cost_rate_provider_model",
        "xynassist_ai_cost_rates",
        ["provider", "model"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_xynassist_ai_cost_rate_provider_model",
        table_name="xynassist_ai_cost_rates",
    )

    op.drop_index(
        op.f(
            "ix_xynassist_ai_cost_rates_model"
        ),
        table_name="xynassist_ai_cost_rates",
    )

    op.drop_index(
        op.f(
            "ix_xynassist_ai_cost_rates_provider"
        ),
        table_name="xynassist_ai_cost_rates",
    )

    op.drop_table(
        "xynassist_ai_cost_rates"
    )
