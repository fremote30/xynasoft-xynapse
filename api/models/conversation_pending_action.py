"""
Durable pending state for trusted conversational actions.

Pending actions are owned by XynaFaith and bind a
confirmation-required action to the authenticated user,
conversation, and exact product resource.
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


class ConversationPendingAction(Base):
    """
    One pending trusted action for a user's conversation.

    Browser input never establishes this record. It is
    created only from trusted server-side product context
    after XynAssist requests explicit confirmation.
    """

    __tablename__ = "conversation_pending_actions"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "conversation_id",
            name=(
                "uq_conversation_pending_action_"
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

    resource_type = Column(
        String(150),
        nullable=False,
    )

    resource_id = Column(
        Integer,
        nullable=False,
    )

    source_message_id = Column(
        String(255),
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
