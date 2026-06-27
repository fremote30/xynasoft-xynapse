"""create jobs table

Revision ID: 0006_create_jobs
Revises: 0005_store_file_blobs
Create Date: 2026-02-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect


revision = "0006_create_jobs"
down_revision = "0005_store_file_blobs"
branch_labels = None
depends_on = None


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "jobs" not in existing_tables:
        op.create_table(
            "jobs",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("job_type", sa.Text(), nullable=False),
            sa.Column("status", sa.Text(), nullable=False, server_default=sa.text("'queued'")),
            sa.Column(
                "payload",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column("error", sa.Text(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )

    inspector = inspect(bind)

    if "jobs" in inspector.get_table_names():
        if not _index_exists(inspector, "jobs", "ix_jobs_status"):
            op.create_index("ix_jobs_status", "jobs", ["status"])

        if not _index_exists(inspector, "jobs", "ix_jobs_job_type"):
            op.create_index("ix_jobs_job_type", "jobs", ["job_type"])

        if not _index_exists(inspector, "jobs", "ix_jobs_created_at"):
            op.create_index("ix_jobs_created_at", "jobs", ["created_at"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if "jobs" in inspector.get_table_names():
        if _index_exists(inspector, "jobs", "ix_jobs_created_at"):
            op.drop_index("ix_jobs_created_at", table_name="jobs")

        if _index_exists(inspector, "jobs", "ix_jobs_job_type"):
            op.drop_index("ix_jobs_job_type", table_name="jobs")

        if _index_exists(inspector, "jobs", "ix_jobs_status"):
            op.drop_index("ix_jobs_status", table_name="jobs")

        op.drop_table("jobs")