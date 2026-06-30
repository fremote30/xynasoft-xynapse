"""add prayer wall engagement tables

Revision ID: 30dec66b204d
Revises: f0f6db5f03db
Create Date: 2026-06-29 06:22:20.749223
"""

from typing import Sequence, Union

from alembic import op


revision: str = "30dec66b204d"
down_revision: Union[str, Sequence[str], None] = "f0f6db5f03db"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Production-safe upgrade.

    Render already has prayers and prayer_reactions, so every table,
    column, index, and constraint must be created defensively.
    """

    # =========================
    # TABLES
    # =========================
    op.execute("""
        CREATE TABLE IF NOT EXISTS prayer_bookmarks (
            id SERIAL PRIMARY KEY,
            prayer_id INTEGER NOT NULL REFERENCES prayers(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            created_at TIMESTAMP WITHOUT TIME ZONE
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS prayer_comments (
            id SERIAL PRIMARY KEY,
            prayer_id INTEGER NOT NULL REFERENCES prayers(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            user_name VARCHAR NOT NULL,
            parent_id INTEGER REFERENCES prayer_comments(id),
            comment TEXT NOT NULL,
            is_pastor_response BOOLEAN,
            is_pinned BOOLEAN,
            is_hidden BOOLEAN,
            created_at TIMESTAMP WITHOUT TIME ZONE,
            updated_at TIMESTAMP WITHOUT TIME ZONE
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS prayer_notifications (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id),
            prayer_id INTEGER REFERENCES prayers(id),
            notification_type VARCHAR NOT NULL,
            message TEXT NOT NULL,
            is_read BOOLEAN,
            created_at TIMESTAMP WITHOUT TIME ZONE
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS prayer_reactions (
            id SERIAL PRIMARY KEY,
            prayer_id INTEGER NOT NULL REFERENCES prayers(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            reaction_type VARCHAR NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE
        );
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS prayer_reports (
            id SERIAL PRIMARY KEY,
            prayer_id INTEGER NOT NULL REFERENCES prayers(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            reason VARCHAR NOT NULL,
            details TEXT,
            created_at TIMESTAMP WITHOUT TIME ZONE
        );
    """)

    # =========================
    # PRAYERS TABLE COLUMNS
    # =========================
    op.execute("ALTER TABLE prayers ADD COLUMN IF NOT EXISTS category VARCHAR;")
    op.execute("ALTER TABLE prayers ADD COLUMN IF NOT EXISTS status VARCHAR;")
    op.execute("ALTER TABLE prayers ADD COLUMN IF NOT EXISTS is_anonymous BOOLEAN;")
    op.execute("ALTER TABLE prayers ADD COLUMN IF NOT EXISTS is_hidden BOOLEAN;")
    op.execute("ALTER TABLE prayers ADD COLUMN IF NOT EXISTS is_locked BOOLEAN;")
    op.execute("ALTER TABLE prayers ADD COLUMN IF NOT EXISTS prayer_count INTEGER;")
    op.execute("ALTER TABLE prayers ADD COLUMN IF NOT EXISTS support_count INTEGER;")
    op.execute("ALTER TABLE prayers ADD COLUMN IF NOT EXISTS comment_count INTEGER;")
    op.execute("ALTER TABLE prayers ADD COLUMN IF NOT EXISTS share_count INTEGER;")
    op.execute("ALTER TABLE prayers ADD COLUMN IF NOT EXISTS answered_at TIMESTAMP WITHOUT TIME ZONE;")
    op.execute("ALTER TABLE prayers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE;")

    # =========================
    # SAFE BACKFILL
    # =========================
    op.execute("""
        UPDATE prayers
        SET
            status = COALESCE(status, 'still_praying'),
            is_anonymous = COALESCE(is_anonymous, false),
            is_hidden = COALESCE(is_hidden, false),
            is_locked = COALESCE(is_locked, false),
            prayer_count = COALESCE(prayer_count, 0),
            support_count = COALESCE(support_count, 0),
            comment_count = COALESCE(comment_count, 0),
            share_count = COALESCE(share_count, 0),
            updated_at = COALESCE(updated_at, created_at);
    """)

    # =========================
    # INDEXES
    # =========================
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_bookmarks_id ON prayer_bookmarks (id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_bookmarks_prayer_id ON prayer_bookmarks (prayer_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_bookmarks_user_id ON prayer_bookmarks (user_id);")

    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_comments_created_at ON prayer_comments (created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_comments_id ON prayer_comments (id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_comments_prayer_id ON prayer_comments (prayer_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_comments_user_id ON prayer_comments (user_id);")

    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_notifications_created_at ON prayer_notifications (created_at);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_notifications_id ON prayer_notifications (id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_notifications_prayer_id ON prayer_notifications (prayer_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_notifications_user_id ON prayer_notifications (user_id);")

    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_reactions_id ON prayer_reactions (id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_reactions_prayer_id ON prayer_reactions (prayer_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_reactions_user_id ON prayer_reactions (user_id);")

    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_reports_id ON prayer_reports (id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_reports_prayer_id ON prayer_reports (prayer_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayer_reports_user_id ON prayer_reports (user_id);")

    op.execute("CREATE INDEX IF NOT EXISTS ix_prayers_category ON prayers (category);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayers_is_hidden ON prayers (is_hidden);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayers_status ON prayers (status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_prayers_user_id ON prayers (user_id);")

    # =========================
    # UNIQUE CONSTRAINTS
    # =========================
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_prayer_user_bookmark'
            ) THEN
                ALTER TABLE prayer_bookmarks
                ADD CONSTRAINT uq_prayer_user_bookmark
                UNIQUE (prayer_id, user_id);
            END IF;
        END $$;
    """)

    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_prayer_user_reaction'
            ) THEN
                ALTER TABLE prayer_reactions
                ADD CONSTRAINT uq_prayer_user_reaction
                UNIQUE (prayer_id, user_id, reaction_type);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    """Safe downgrade for development only."""

    op.execute("DROP TABLE IF EXISTS prayer_reports CASCADE;")
    op.execute("DROP TABLE IF EXISTS prayer_notifications CASCADE;")
    op.execute("DROP TABLE IF EXISTS prayer_comments CASCADE;")
    op.execute("DROP TABLE IF EXISTS prayer_bookmarks CASCADE;")

    # Do not drop prayers or prayer_reactions in production because they may pre-exist.
    op.execute("DROP INDEX IF EXISTS ix_prayers_user_id;")
    op.execute("DROP INDEX IF EXISTS ix_prayers_status;")
    op.execute("DROP INDEX IF EXISTS ix_prayers_is_hidden;")
    op.execute("DROP INDEX IF EXISTS ix_prayers_category;")