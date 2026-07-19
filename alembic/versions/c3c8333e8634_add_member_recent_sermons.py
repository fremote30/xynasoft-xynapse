"""add member recent sermons

Revision ID: c3c8333e8634
Revises: e5a42c69e939
Create Date: 2026-07-15 03:02:33.219494
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3c8333e8634"
down_revision: Union[str, Sequence[str], None] = "e5a42c69e939"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the member recent sermons table."""

    op.create_table(
        "member_recent_sermons",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "member_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "sermon_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "last_opened_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False
        ),

        sa.ForeignKeyConstraint(
            ["member_id"],
            ["users.id"],
            ondelete="CASCADE"
        ),

        sa.ForeignKeyConstraint(
            ["sermon_id"],
            ["sermons.id"],
            ondelete="CASCADE"
        ),

        sa.PrimaryKeyConstraint("id"),

        sa.UniqueConstraint(
            "member_id",
            "sermon_id",
            name="uq_member_recent_sermon"
        )
    )

    op.create_index(
        "ix_member_recent_sermons_id",
        "member_recent_sermons",
        ["id"],
        unique=False
    )

    op.create_index(
        "ix_member_recent_sermons_member_id",
        "member_recent_sermons",
        ["member_id"],
        unique=False
    )

    op.create_index(
        "ix_member_recent_sermons_sermon_id",
        "member_recent_sermons",
        ["sermon_id"],
        unique=False
    )


def downgrade() -> None:
    """Remove the member recent sermons table."""

    op.drop_index(
        "ix_member_recent_sermons_sermon_id",
        table_name="member_recent_sermons"
    )

    op.drop_index(
        "ix_member_recent_sermons_member_id",
        table_name="member_recent_sermons"
    )

    op.drop_index(
        "ix_member_recent_sermons_id",
        table_name="member_recent_sermons"
    )

    op.drop_table(
        "member_recent_sermons"
    )