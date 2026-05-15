from __future__ import annotations

from sqlalchemy import text
from storage.db import engine

# NOTE:
# - Postgres: use UUID + JSONB and default UUID generation
# - SQLite: will ignore UUID/JSONB types unless you run this there (not recommended)
TABLES_POSTGRES = [
    """
    CREATE TABLE IF NOT EXISTS documents (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        filename TEXT NOT NULL,
        sha256 TEXT NOT NULL,
        raw_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chunks (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        chunk_index INTEGER NOT NULL,
        content TEXT NOT NULL,
        embedding JSONB,
        embedding_model TEXT,
        embedding_dim INTEGER,
        embedded_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        endpoint TEXT NOT NULL,
        details JSONB NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    # Helpful index for FTS (optional but recommended)
    """
    CREATE INDEX IF NOT EXISTS idx_chunks_content_tsv
    ON chunks
    USING gin (to_tsvector('english', content))
    """

        # Jobs table (queue scaffolding)
    """
    CREATE TABLE IF NOT EXISTS jobs (
        id UUID PRIMARY KEY,
        job_type TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'queued',  -- queued|running|succeeded|failed
        payload JSONB NOT NULL DEFAULT '{}'::jsonb,
        result JSONB,
        error TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """

]

# If you ever run SQLite again, you’d use a different schema.
# For "Postgres now", we keep it strict and clear.

def main():
    with engine.begin() as conn:
        if engine.dialect.name != "postgresql":
            raise RuntimeError(
                f"init_db.py is currently Postgres-only. dialect={engine.dialect.name}. "
                f"Set DATABASE_URL to Postgres."
            )

        # Extensions needed for gen_random_uuid() and (later) embeddings
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pgcrypto"))
        # When ready for embeddings:
        # conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

        for ddl in TABLES_POSTGRES:
            conn.execute(text(ddl))

    print(f"init_db complete (dialect={engine.dialect.name})")


if __name__ == "__main__":
    main()
