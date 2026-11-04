"""scope reading plans to Church Spaces

Revision ID: e1a5b01
Revises: d9f4a01
"""

from alembic import op
import sqlalchemy as sa


revision = "e1a5b01"
down_revision = "d9f4a01"
branch_labels = None
depends_on = None


def upgrade():
    # The V2 reading-plan foundation has not yet accumulated
    # production data, so Church Space ownership is required
    # immediately rather than introduced as a transitional nullable
    # field.
    op.add_column(
        "reading_plans",
        sa.Column(
            "church_id",
            sa.Integer(),
            nullable=False,
        ),
    )

    op.create_foreign_key(
        "fk_reading_plans_church_id_churches",
        "reading_plans",
        "churches",
        ["church_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index(
        "ix_reading_plans_church_id",
        "reading_plans",
        ["church_id"],
        unique=False,
    )

    op.add_column(
        "reading_plans",
        sa.Column(
            "published_at",
            sa.DateTime(),
            nullable=True,
        ),
    )

    op.drop_index(
        "ix_reading_plans_status_created",
        table_name="reading_plans",
    )

    op.create_index(
        "ix_reading_plans_church_status",
        "reading_plans",
        ["church_id", "status"],
        unique=False,
    )

    op.create_index(
        "ix_reading_plans_church_published",
        "reading_plans",
        ["church_id", "published_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_reading_plans_church_published",
        table_name="reading_plans",
    )

    op.drop_index(
        "ix_reading_plans_church_status",
        table_name="reading_plans",
    )

    op.create_index(
        "ix_reading_plans_status_created",
        "reading_plans",
        ["status", "created_at"],
        unique=False,
    )

    op.drop_column(
        "reading_plans",
        "published_at",
    )

    op.drop_index(
        "ix_reading_plans_church_id",
        table_name="reading_plans",
    )

    op.drop_constraint(
        "fk_reading_plans_church_id_churches",
        "reading_plans",
        type_="foreignkey",
    )

    op.drop_column(
        "reading_plans",
        "church_id",
    )
