"""add pgvector embeddings to chunks

Revision ID: 9a989471a9c8
Revises: c32676206d78
Create Date: <AUTO>
"""
from alembic import op
import sqlalchemy as sa

revision = "9a989471a9c8"
down_revision = "c32676206d78"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1) Enable pgvector
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2) If an old jsonb embedding exists, preserve it by renaming
    #    (only if column exists AND is not already the vector type)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='chunks'
                  AND column_name='embedding'
            ) THEN
                -- If embedding is not a vector column, rename it
                IF NOT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_name='chunks'
                      AND column_name='embedding'
                      AND udt_name='vector'
                ) THEN
                    -- Avoid double-rename
                    IF NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name='chunks'
                          AND column_name='embedding_json'
                    ) THEN
                        ALTER TABLE chunks RENAME COLUMN embedding TO embedding_json;
                    ELSE
                        -- If embedding_json already exists, just drop the old embedding
                        ALTER TABLE chunks DROP COLUMN embedding;
                    END IF;
                END IF;
            END IF;
        END
        $$;
        """
    )

    # 3) Ensure the real vector column exists
    op.execute("ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding vector(1536)")

    # 4) Add embedded_at if missing
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_name='chunks'
                  AND column_name='embedded_at'
            ) THEN
                ALTER TABLE chunks ADD COLUMN embedded_at timestamptz NULL;
            END IF;
        END
        $$;
        """
    )

    # 5) Vector index (ivfflat). NOTE: ivfflat works best after you have data + ANALYZE.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_chunks_embedding_ivfflat
        ON chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)
        """
    )


def downgrade() -> None:
    # Drop vector search index/cols (keep embedding_json if it exists)
    op.execute("DROP INDEX IF EXISTS ix_chunks_embedding_ivfflat")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS embedded_at")
    op.execute("ALTER TABLE chunks DROP COLUMN IF EXISTS embedding")
    # keep extension installed
