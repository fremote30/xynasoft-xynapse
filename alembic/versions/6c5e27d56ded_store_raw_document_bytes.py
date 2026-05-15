from alembic import op

# revision identifiers, used by Alembic.
revision = "0003_files"
down_revision = "0002_indexes"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE IF NOT EXISTS document_files (
        id UUID PRIMARY KEY,
        document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
        content_type TEXT NOT NULL,
        data BYTEA NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_document_files_document_id ON document_files(document_id);")


def downgrade():
    op.execute("DROP TABLE IF EXISTS document_files;")
