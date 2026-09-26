"""add V2 member engagement foundation

Revision ID: d9f4a01
Revises: c8e3d01
"""

from alembic import op
import sqlalchemy as sa


revision = "d9f4a01"
down_revision = "c8e3d01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reading_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("creator_user_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["creator_user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reading_plans_creator_user_id",
        "reading_plans",
        ["creator_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_reading_plans_status_created",
        "reading_plans",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "reading_plan_days",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("scripture", sa.String(length=500), nullable=False),
        sa.Column("reflection", sa.Text(), nullable=True),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["reading_plans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_reading_plan_days_plan_id",
        "reading_plan_days",
        ["plan_id"],
        unique=False,
    )
    op.create_index(
        "ux_reading_plan_day_number",
        "reading_plan_days",
        ["plan_id", "day_number"],
        unique=True,
    )

    op.create_table(
        "member_reading_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default="active",
        ),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["reading_plans.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_member_reading_plans_plan_id",
        "member_reading_plans",
        ["plan_id"],
        unique=False,
    )
    op.create_index(
        "ix_member_reading_plans_user_id",
        "member_reading_plans",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ux_member_reading_plan",
        "member_reading_plans",
        ["user_id", "plan_id"],
        unique=True,
    )

    op.create_table(
        "member_reading_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("enrollment_id", sa.Integer(), nullable=False),
        sa.Column("day_id", sa.Integer(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["day_id"],
            ["reading_plan_days.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["enrollment_id"],
            ["member_reading_plans.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_member_reading_progress_day_id",
        "member_reading_progress",
        ["day_id"],
        unique=False,
    )
    op.create_index(
        "ix_member_reading_progress_enrollment_id",
        "member_reading_progress",
        ["enrollment_id"],
        unique=False,
    )
    op.create_index(
        "ux_member_reading_progress_day",
        "member_reading_progress",
        ["enrollment_id", "day_id"],
        unique=True,
    )

    op.create_table(
        "member_sermon_notes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sermon_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["sermon_id"],
            ["sermons.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_member_sermon_notes_sermon_id",
        "member_sermon_notes",
        ["sermon_id"],
        unique=False,
    )
    op.create_index(
        "ix_member_sermon_notes_user_id",
        "member_sermon_notes",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_member_sermon_notes_user_updated",
        "member_sermon_notes",
        ["user_id", "updated_at"],
        unique=False,
    )


def downgrade():
    op.drop_index(
        "ix_member_sermon_notes_user_updated",
        table_name="member_sermon_notes",
    )
    op.drop_index(
        "ix_member_sermon_notes_user_id",
        table_name="member_sermon_notes",
    )
    op.drop_index(
        "ix_member_sermon_notes_sermon_id",
        table_name="member_sermon_notes",
    )
    op.drop_table("member_sermon_notes")

    op.drop_index(
        "ux_member_reading_progress_day",
        table_name="member_reading_progress",
    )
    op.drop_index(
        "ix_member_reading_progress_enrollment_id",
        table_name="member_reading_progress",
    )
    op.drop_index(
        "ix_member_reading_progress_day_id",
        table_name="member_reading_progress",
    )
    op.drop_table("member_reading_progress")

    op.drop_index(
        "ux_member_reading_plan",
        table_name="member_reading_plans",
    )
    op.drop_index(
        "ix_member_reading_plans_user_id",
        table_name="member_reading_plans",
    )
    op.drop_index(
        "ix_member_reading_plans_plan_id",
        table_name="member_reading_plans",
    )
    op.drop_table("member_reading_plans")

    op.drop_index(
        "ux_reading_plan_day_number",
        table_name="reading_plan_days",
    )
    op.drop_index(
        "ix_reading_plan_days_plan_id",
        table_name="reading_plan_days",
    )
    op.drop_table("reading_plan_days")

    op.drop_index(
        "ix_reading_plans_status_created",
        table_name="reading_plans",
    )
    op.drop_index(
        "ix_reading_plans_creator_user_id",
        table_name="reading_plans",
    )
    op.drop_table("reading_plans")
