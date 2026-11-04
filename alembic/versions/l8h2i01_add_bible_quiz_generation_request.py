"""Add Bible Quiz AI generation request tracking.

Revision ID: l8h2i01
Revises: k7g1h01
"""

from alembic import op
import sqlalchemy as sa


revision = "l8h2i01"
down_revision = "k7g1h01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "bible_quizzes",
        sa.Column(
            "generation_request_id",
            sa.String(length=128),
            nullable=True,
        ),
    )

    op.add_column(
        "bible_quizzes",
        sa.Column(
            "generation_input_hash",
            sa.String(length=64),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_bible_quizzes_generation_request_id",
        "bible_quizzes",
        ["generation_request_id"],
        unique=True,
    )


def downgrade():
    op.drop_index(
        "ix_bible_quizzes_generation_request_id",
        table_name="bible_quizzes",
    )

    op.drop_column(
        "bible_quizzes",
        "generation_input_hash",
    )

    op.drop_column(
        "bible_quizzes",
        "generation_request_id",
    )
