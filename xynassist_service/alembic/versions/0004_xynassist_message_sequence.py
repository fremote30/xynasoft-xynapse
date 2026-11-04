"""add deterministic XynAssist message ordering

Revision ID: 0004_xynassist
Revises: 0003_xynassist
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_xynassist"
down_revision = "0003_xynassist"
branch_labels = None
depends_on = None


SEQUENCE_NAME = "xynassist_message_sequence"
TABLE_NAME = "xynassist_conversation_messages"


def upgrade():
    # A database sequence gives newly persisted messages a
    # concurrency-safe, monotonic ordering key.
    op.execute(
        f"CREATE SEQUENCE {SEQUENCE_NAME} START WITH 1"
    )

    op.add_column(
        TABLE_NAME,
        sa.Column(
            "sequence_number",
            sa.BigInteger(),
            nullable=True,
        ),
    )

    # Backfill existing messages.
    #
    # Completed turn records are authoritative about which user
    # and assistant messages belong to the same logical turn.
    # Their turn creation time is therefore used as the primary
    # grouping key, with user before assistant inside each turn.
    #
    # Legacy messages that are not referenced by a turn fall back
    # to their persisted message timestamp. UUID is used only as a
    # final deterministic tie breaker; it is not treated as
    # historical chronology.
    op.execute(
        f"""
        WITH message_order AS (
            SELECT
                m.id,
                row_number() OVER (
                    ORDER BY
                        COALESCE(
                            t.created_at,
                            m.created_at
                        ) ASC,
                        COALESCE(t.id, m.id) ASC,
                        CASE
                            WHEN t.user_message_id = m.id
                                THEN 0
                            WHEN t.assistant_message_id = m.id
                                THEN 1
                            WHEN m.role = 'user'
                                THEN 2
                            WHEN m.role = 'assistant'
                                THEN 3
                            ELSE 4
                        END ASC,
                        m.id ASC
                ) AS sequence_number
            FROM {TABLE_NAME} AS m
            LEFT JOIN xynassist_conversation_turns AS t
                ON (
                    t.user_message_id = m.id
                    OR t.assistant_message_id = m.id
                )
        )
        UPDATE {TABLE_NAME} AS m
        SET sequence_number = message_order.sequence_number
        FROM message_order
        WHERE m.id = message_order.id
        """
    )

    # Continue the PostgreSQL sequence after the largest backfilled
    # value. setval(..., false) means the next nextval() returns
    # exactly max + 1.
    op.execute(
        f"""
        SELECT setval(
            '{SEQUENCE_NAME}',
            COALESCE(
                (
                    SELECT MAX(sequence_number) + 1
                    FROM {TABLE_NAME}
                ),
                1
            ),
            false
        )
        """
    )

    op.alter_column(
        TABLE_NAME,
        "sequence_number",
        nullable=False,
        server_default=sa.text(
            f"nextval('{SEQUENCE_NAME}')"
        ),
    )

    op.create_index(
        "ix_xynassist_conversation_messages_sequence_number",
        TABLE_NAME,
        ["sequence_number"],
        unique=True,
    )


def downgrade():
    op.drop_index(
        "ix_xynassist_conversation_messages_sequence_number",
        table_name=TABLE_NAME,
    )

    op.drop_column(
        TABLE_NAME,
        "sequence_number",
    )

    op.execute(
        f"DROP SEQUENCE {SEQUENCE_NAME}"
    )
