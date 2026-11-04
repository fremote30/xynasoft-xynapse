"""add indexes for explorer and search

Revision ID: 0002_indexes
Revises: 0001_baseline
Create Date: 2026-01-31
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_indexes"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade():
    # Documents
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_created_at ON documents (created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_documents_sha256 ON documents (sha256)")

    # Chunks
    op.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks (document_id)")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_chunks_doc_chunk_index ON chunks (document_id, chunk_index)")

    # Full-text search index (Postgres)
    # This matches your queries.py approach: to_tsvector('english', content)
    op.execute("""
    CREATE INDEX IF NOT EXISTS idx_chunks_content_tsv
    ON chunks
    USING GIN (to_tsvector('english', content))
    """)


def downgrade():
    op.execute("DROP INDEX IF EXISTS idx_chunks_content_tsv")
    op.execute("DROP INDEX IF EXISTS uq_chunks_doc_chunk_index")
    op.execute("DROP INDEX IF EXISTS idx_chunks_document_id")
    op.execute("DROP INDEX IF EXISTS idx_documents_sha256")
    op.execute("DROP INDEX IF EXISTS idx_documents_created_at")
