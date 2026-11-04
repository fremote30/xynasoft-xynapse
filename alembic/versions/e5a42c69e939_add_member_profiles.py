"""add member profiles

Revision ID: e5a42c69e939
Revises: 7cb871b1985e
Create Date: 2026-07-12 02:03:31.182356
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e5a42c69e939"
down_revision: Union[str, Sequence[str], None] = "7cb871b1985e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create member profile table."""

    op.create_table(
        "member_profiles",

        sa.Column(
            "id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False
        ),

        sa.Column(
            "bio",
            sa.Text(),
            nullable=True
        ),

        sa.Column(
            "profile_image",
            sa.String(),
            nullable=True
        ),

        sa.Column(
            "favorite_scripture",
            sa.String(),
            nullable=True
        ),

        sa.Column(
            "city",
            sa.String(),
            nullable=True
        ),

        sa.Column(
            "state",
            sa.String(),
            nullable=True
        ),

        sa.Column(
            "country",
            sa.String(),
            nullable=True
        ),

        sa.Column(
            "languages",
            sa.String(),
            nullable=True
        ),

        sa.Column(
            "church_name",
            sa.String(),
            nullable=True
        ),

        sa.Column(
            "ministry_interests",
            sa.Text(),
            nullable=True
        ),

        sa.Column(
            "prayer_interests",
            sa.Text(),
            nullable=True
        ),

        sa.Column(
            "visibility",
            sa.String(length=20),
            nullable=False,
            server_default="members"
        ),

        sa.Column(
            "allow_direct_messages",
            sa.Boolean(),
            nullable=True,
            server_default=sa.true()
        ),

        sa.Column(
            "receive_notifications",
            sa.Boolean(),
            nullable=True,
            server_default=sa.true()
        ),

        sa.Column(
            "slug",
            sa.String(),
            nullable=True
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True
        ),

        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE"
        ),

        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            name="uq_member_profiles_user_id"
        ),
        sa.UniqueConstraint(
            "slug",
            name="uq_member_profiles_slug"
        )
    )

    op.create_index(
        "ix_member_profiles_id",
        "member_profiles",
        ["id"],
        unique=False
    )

    op.create_index(
        "ix_member_profiles_user_id",
        "member_profiles",
        ["user_id"],
        unique=True
    )

    op.create_index(
        "ix_member_profiles_slug",
        "member_profiles",
        ["slug"],
        unique=True
    )


def downgrade() -> None:
    """Remove member profile table."""

    op.drop_index(
        "ix_member_profiles_slug",
        table_name="member_profiles"
    )

    op.drop_index(
        "ix_member_profiles_user_id",
        table_name="member_profiles"
    )

    op.drop_index(
        "ix_member_profiles_id",
        table_name="member_profiles"
    )

    op.drop_table("member_profiles")