"""
Durable pending state for conversational XynAssist memory actions.

A pending memory action is owned by XynaFaith and binds an
explicit-confirmation action to the authenticated user,
conversation, and exact logical memory identity.

Browser input never establishes this record.
"""

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)

from api.db.database import Base


class ConversationPendingMemoryAction(Base):
    """
    One pending memory action for a user's conversation.

    Memory identity is logical (memory_type + memory_key).
    XynAssist internal memory identifiers are intentionally
    not exposed to or persisted by XynaFaith.
    """

    __tablename__ = (
        "conversation_pending_memory_actions"
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "conversation_id",
            name=(
                "uq_conversation_pending_memory_action_"
                "user_conversation"
            ),
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    conversation_id = Column(
        String(36),
        nullable=False,
        index=True,
    )

    action_name = Column(
        String(150),
        nullable=False,
    )

    memory_type = Column(
        String(64),
        nullable=False,
    )

    memory_key = Column(
        String(255),
        nullable=False,
    )

    source_message_id = Column(
        String(255),
        nullable=False,
    )

    action_request_id = Column(
        String(36),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
