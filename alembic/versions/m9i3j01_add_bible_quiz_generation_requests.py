"""Add durable Bible Quiz generation request records.

Revision ID: m9i3j01
Revises: l8h2i01
"""

from alembic import op
import sqlalchemy as sa


revision = "m9i3j01"
down_revision = "l8h2i01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "bible_quiz_generation_requests",
        sa.Column(
            "request_id",
            sa.String(length=128),
            primary_key=True,
        ),
        sa.Column(
            "church_id",
            sa.Integer(),
            sa.ForeignKey("churches.id"),
            nullable=False,
        ),
        sa.Column(
            "creator_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "input_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
        ),
    )

    op.create_index(
        "ix_bible_quiz_generation_requests_church_id",
        "bible_quiz_generation_requests",
        ["church_id"],
    )

    op.create_index(
        "ix_bible_quiz_generation_requests_creator_user_id",
        "bible_quiz_generation_requests",
        ["creator_user_id"],
    )


def downgrade():
    op.drop_index(
        "ix_bible_quiz_generation_requests_creator_user_id",
        table_name="bible_quiz_generation_requests",
    )

    op.drop_index(
        "ix_bible_quiz_generation_requests_church_id",
        table_name="bible_quiz_generation_requests",
    )

    op.drop_table("bible_quiz_generation_requests")
