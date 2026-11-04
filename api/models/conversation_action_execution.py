from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from api.db.database import Base


class ConversationActionExecution(Base):
    """
    Durable record of a trusted conversational action.

    The authenticated XynaFaith user plus XynaFaith's
    stable request identifier form the durable idempotency
    boundary. The XynAssist user-message identifier is kept
    separately for provenance.
    """

    __tablename__ = "conversation_action_executions"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "request_id",
            name=(
                "uq_conversation_action_execution_"
                "user_request"
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
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    request_id = Column(
        String(36),
        nullable=False,
    )

    source_message_id = Column(
        String(255),
        nullable=False,
    )

    action_name = Column(
        String(150),
        nullable=False,
    )

    status = Column(
        String(32),
        nullable=False,
        default="completed",
    )

    result = Column(
        JSONB,
        nullable=False,
        default=dict,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
