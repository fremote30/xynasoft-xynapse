"""store raw file bytes (document_files + document_blobs) and add file metadata to documents

Revision ID: 0005_store_file_blobs
Revises: 0004_merge_heads
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "0005_store_file_blobs"
down_revision = "0004_merge_heads"
branch_labels = None
depends_on = None


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _index_exists(inspector, table_name: str, index_name: str) -> bool:
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    existing_tables = inspector.get_table_names()

    # 1) Add file metadata columns to documents safely
    if "documents" in existing_tables:
        if not _column_exists(inspector, "documents", "content_type"):
            op.add_column("documents", sa.Column("content_type", sa.Text(), nullable=True))

        if not _column_exists(inspector, "documents", "bytes_size"):
            op.add_column("documents", sa.Column("bytes_size", sa.BigInteger(), nullable=True))

    # 2) Store raw uploaded bytes in document_blobs safely
    if "document_blobs" not in existing_tables:
        op.create_table(
            "document_blobs",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("content_type", sa.Text(), nullable=False),
            sa.Column("data", postgresql.BYTEA(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
            sa.UniqueConstraint("document_id", name="uq_document_blobs_document_id"),
        )

    inspector = inspect(bind)

    if "document_blobs" in inspector.get_table_names():
        if not _index_exists(inspector, "document_blobs", "ix_document_blobs_document_id"):
            op.create_index(
                "ix_document_blobs_document_id",
                "document_blobs",
                ["document_id"],
            )

    # 3) Optional: store additional file versions/attachments safely
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "document_files" not in existing_tables:
        op.create_table(
            "document_files",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("content_type", sa.Text(), nullable=False),
            sa.Column("data", postgresql.BYTEA(), nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        )

    inspector = inspect(bind)

    if "document_files" in inspector.get_table_names():
        if not _index_exists(inspector, "document_files", "ix_document_files_document_id"):
            op.create_index(
                "ix_document_files_document_id",
                "document_files",
                ["document_id"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "document_files" in existing_tables:
        if _index_exists(inspector, "document_files", "ix_document_files_document_id"):
            op.drop_index("ix_document_files_document_id", table_name="document_files")
        op.drop_table("document_files")

    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "document_blobs" in existing_tables:
        if _index_exists(inspector, "document_blobs", "ix_document_blobs_document_id"):
            op.drop_index("ix_document_blobs_document_id", table_name="document_blobs")
        op.drop_table("document_blobs")

    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()

    if "documents" in existing_tables:
        if _column_exists(inspector, "documents", "bytes_size"):
            op.drop_column("documents", "bytes_size")

        if _column_exists(inspector, "documents", "content_type"):
            op.drop_column("documents", "content_type")