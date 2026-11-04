"""add faith sermons and questions

Revision ID: e3d7e3f9897a
Revises: 9a989471a9c8
Create Date: 2026-02-22 07:44:58.327935

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3d7e3f9897a'
down_revision: Union[str, Sequence[str], None] = '9a989471a9c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade():
    op.create_table(
        "faith_sermons",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("pastor_id", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("payload_input", sa.JSON(), nullable=False),
        sa.Column("payload_output", sa.JSON(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("share_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_faith_sermons_created_at", "faith_sermons", ["created_at"])
    op.create_unique_constraint("uq_faith_sermons_share_id", "faith_sermons", ["share_id"])

    op.create_table(
        "faith_questions",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("sermon_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_faith_questions_sermon_id", "faith_questions", ["sermon_id"])


def downgrade():
    op.drop_index("ix_faith_questions_sermon_id", table_name="faith_questions")
    op.drop_table("faith_questions")

    op.drop_constraint("uq_faith_sermons_share_id", "faith_sermons", type_="unique")
    op.drop_index("ix_faith_sermons_created_at", table_name="faith_sermons")
    op.drop_table("faith_sermons")