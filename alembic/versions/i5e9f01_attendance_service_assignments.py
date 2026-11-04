"""add attendance and service assignments

Revision ID: i5e9f01
Revises: h4d8e01
"""

from alembic import op
import sqlalchemy as sa


revision = "i5e9f01"
down_revision = "h4d8e01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "church_attendance_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("church_membership_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="present",
            nullable=False,
        ),
        sa.Column("recorded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("checked_in_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["church_events.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["church_membership_id"],
            ["church_memberships.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["recorded_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id",
            "church_membership_id",
            name="uq_church_attendance_event_membership",
        ),
    )

    op.create_index(
        "ix_church_attendance_records_event_id",
        "church_attendance_records",
        ["event_id"],
    )
    op.create_index(
        "ix_church_attendance_records_church_membership_id",
        "church_attendance_records",
        ["church_membership_id"],
    )
    op.create_index(
        "ix_church_attendance_records_recorded_by_user_id",
        "church_attendance_records",
        ["recorded_by_user_id"],
    )

    op.create_table(
        "church_service_assignments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_id", sa.Integer(), nullable=False),
        sa.Column("group_id", sa.Integer(), nullable=False),
        sa.Column("church_membership_id", sa.Integer(), nullable=False),
        sa.Column("service_role", sa.String(length=120), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            server_default="assigned",
            nullable=False,
        ),
        sa.Column("assigned_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["event_id"],
            ["church_events.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["group_id"],
            ["church_groups.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["church_membership_id"],
            ["church_memberships.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"],
            ["users.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "event_id",
            "group_id",
            "church_membership_id",
            "service_role",
            name="uq_church_service_assignment",
        ),
    )

    op.create_index(
        "ix_church_service_assignments_event_id",
        "church_service_assignments",
        ["event_id"],
    )
    op.create_index(
        "ix_church_service_assignments_group_id",
        "church_service_assignments",
        ["group_id"],
    )
    op.create_index(
        "ix_church_service_assignments_church_membership_id",
        "church_service_assignments",
        ["church_membership_id"],
    )
    op.create_index(
        "ix_church_service_assignments_assigned_by_user_id",
        "church_service_assignments",
        ["assigned_by_user_id"],
    )


def downgrade():
    op.drop_index(
        "ix_church_service_assignments_assigned_by_user_id",
        table_name="church_service_assignments",
    )
    op.drop_index(
        "ix_church_service_assignments_church_membership_id",
        table_name="church_service_assignments",
    )
    op.drop_index(
        "ix_church_service_assignments_group_id",
        table_name="church_service_assignments",
    )
    op.drop_index(
        "ix_church_service_assignments_event_id",
        table_name="church_service_assignments",
    )
    op.drop_table("church_service_assignments")

    op.drop_index(
        "ix_church_attendance_records_recorded_by_user_id",
        table_name="church_attendance_records",
    )
    op.drop_index(
        "ix_church_attendance_records_church_membership_id",
        table_name="church_attendance_records",
    )
    op.drop_index(
        "ix_church_attendance_records_event_id",
        table_name="church_attendance_records",
    )
    op.drop_table("church_attendance_records")
