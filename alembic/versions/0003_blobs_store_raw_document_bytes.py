from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_blobs"
down_revision = "0002_indexes"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_blobs (
            document_id UUID PRIMARY KEY REFERENCES documents(id) ON DELETE CASCADE,
            content_type TEXT NOT NULL,
            bytes BYTEA NOT NULL,
            size_bytes INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_document_blobs_created_at
            ON document_blobs(created_at);
        """
    )


def downgrade():
    op.execute("DROP TABLE IF EXISTS document_blobs;")
