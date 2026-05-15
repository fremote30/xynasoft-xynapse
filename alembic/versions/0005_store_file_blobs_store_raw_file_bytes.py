"""store raw file bytes (document_files + document_blobs) and add file metadata to documents

Revision ID: 0005_store_file_blobs
Revises: 0004_merge_heads
Create Date: 2026-02-10
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "0005_store_file_blobs"
down_revision = "0004_merge_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Add file metadata columns to documents (used by UI + analytics)
    op.add_column("documents", sa.Column("content_type", sa.Text(), nullable=True))
    op.add_column("documents", sa.Column("bytes_size", sa.BigInteger(), nullable=True))

    # 2) Store raw uploaded bytes in document_blobs (one blob per document)
    op.create_table(
        "document_blobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("data", postgresql.BYTEA(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("document_id", name="uq_document_blobs_document_id"),
    )
    op.create_index("ix_document_blobs_document_id", "document_blobs", ["document_id"])

    # 3) Optional: store additional file versions/attachments (multiple per document)
    op.create_table(
        "document_files",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content_type", sa.Text(), nullable=False),
        sa.Column("data", postgresql.BYTEA(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["document_id"], ["documents.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_document_files_document_id", "document_files", ["document_id"])


def downgrade() -> None:
    # drop children first
    op.drop_index("ix_document_files_document_id", table_name="document_files")
    op.drop_table("document_files")

    op.drop_index("ix_document_blobs_document_id", table_name="document_blobs")
    op.drop_table("document_blobs")

    # then columns
    op.drop_column("documents", "bytes_size")
    op.drop_column("documents", "content_type")
