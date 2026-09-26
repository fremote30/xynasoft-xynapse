"""add V2 pastoral care workflow

Revision ID: b7d2c01
Revises: a6b6c01
"""

from alembic import op
import sqlalchemy as sa


revision = "b7d2c01"
down_revision = "a6b6c01"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "prayers",
        sa.Column("church_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "prayers",
        sa.Column(
            "pastoral_care_requested",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    op.create_foreign_key(
        "fk_prayers_church_id_churches",
        "prayers",
        "churches",
        ["church_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_prayers_church_id",
        "prayers",
        ["church_id"],
        unique=False,
    )

    op.create_table(
        "pastoral_care_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("church_id", sa.Integer(), nullable=False),
        sa.Column("prayer_id", sa.Integer(), nullable=False),
        sa.Column("member_user_id", sa.Integer(), nullable=False),
        sa.Column("assigned_to_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="open",
        ),
        sa.Column(
            "priority",
            sa.String(length=32),
            nullable=False,
            server_default="routine",
        ),
        sa.Column("follow_up_at", sa.DateTime(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["church_id"],
            ["churches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["prayer_id"],
            ["prayers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["member_user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_to_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "prayer_id",
            name="uq_pastoral_care_cases_prayer_id",
        ),
    )

    op.create_index(
        "ix_pastoral_care_cases_church_id",
        "pastoral_care_cases",
        ["church_id"],
    )
    op.create_index(
        "ix_pastoral_care_cases_prayer_id",
        "pastoral_care_cases",
        ["prayer_id"],
        unique=True,
    )
    op.create_index(
        "ix_pastoral_care_cases_member_user_id",
        "pastoral_care_cases",
        ["member_user_id"],
    )
    op.create_index(
        "ix_pastoral_care_cases_assigned_to_user_id",
        "pastoral_care_cases",
        ["assigned_to_user_id"],
    )
    op.create_index(
        "ix_pastoral_care_cases_church_status",
        "pastoral_care_cases",
        ["church_id", "status"],
    )
    op.create_index(
        "ix_pastoral_care_cases_church_assignee",
        "pastoral_care_cases",
        ["church_id", "assigned_to_user_id"],
    )
    op.create_index(
        "ix_pastoral_care_cases_church_follow_up",
        "pastoral_care_cases",
        ["church_id", "follow_up_at"],
    )

    op.create_table(
        "pastoral_care_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("church_id", sa.Integer(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["pastoral_care_cases.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["church_id"],
            ["churches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_pastoral_care_notes_case_id",
        "pastoral_care_notes",
        ["case_id"],
    )
    op.create_index(
        "ix_pastoral_care_notes_church_id",
        "pastoral_care_notes",
        ["church_id"],
    )
    op.create_index(
        "ix_pastoral_care_notes_author_user_id",
        "pastoral_care_notes",
        ["author_user_id"],
    )
    op.create_index(
        "ix_pastoral_care_notes_church_case",
        "pastoral_care_notes",
        ["church_id", "case_id"],
    )

    op.create_table(
        "pastoral_care_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("church_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("activity_type", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["pastoral_care_cases.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["church_id"],
            ["churches.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_pastoral_care_activities_case_id",
        "pastoral_care_activities",
        ["case_id"],
    )
    op.create_index(
        "ix_pastoral_care_activities_church_id",
        "pastoral_care_activities",
        ["church_id"],
    )
    op.create_index(
        "ix_pastoral_care_activities_actor_user_id",
        "pastoral_care_activities",
        ["actor_user_id"],
    )
    op.create_index(
        "ix_pastoral_care_activities_activity_type",
        "pastoral_care_activities",
        ["activity_type"],
    )
    op.create_index(
        "ix_pastoral_care_activities_church_case",
        "pastoral_care_activities",
        ["church_id", "case_id"],
    )


def downgrade():
    op.drop_table("pastoral_care_activities")
    op.drop_table("pastoral_care_notes")
    op.drop_table("pastoral_care_cases")

    op.drop_index("ix_prayers_church_id", table_name="prayers")
    op.drop_constraint(
        "fk_prayers_church_id_churches",
        "prayers",
        type_="foreignkey",
    )
    op.drop_column("prayers", "pastoral_care_requested")
    op.drop_column("prayers", "church_id")
