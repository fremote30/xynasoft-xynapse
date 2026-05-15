"""baseline schema

Revision ID: 0001_baseline
Revises: 
Create Date: 2026-01-31
"""

from alembic import op
import sqlalchemy as sa


# ==============================
# Alembic identifiers
# ==============================
revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


# ==============================
# Upgrade (apply schema)
# ==============================
def upgrade():
    # Enable Postgres UUID support (safe to run multiple times)
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # --------------------------
    # Documents
    # --------------------------
    op.execute("""
    CREATE TABLE documents (
        id UUID PRIMARY KEY,
        filename TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        raw_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # --------------------------
    # Chunks
    # --------------------------
    op.execute("""
    CREATE TABLE chunks (
        id UUID PRIMARY KEY,
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding JSONB,
        embedding_model TEXT,
        embedding_dim INTEGER,
        embedded_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # --------------------------
    # Audit logs
    # --------------------------
    op.execute("""
    CREATE TABLE audit_logs (
        id UUID PRIMARY KEY,
        endpoint TEXT NOT NULL,
        details JSONB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)


# ==============================
# Downgrade (rollback schema)
# ==============================
def downgrade():
    # Drop in reverse dependency order
    op.execute("DROP TABLE IF EXISTS audit_logs")
    op.execute("DROP TABLE IF EXISTS chunks")
    op.execute("DROP TABLE IF EXISTS documents")
