"""
Persistent XynAssist conversation message model.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)

from xynassist_service.db.database import Base


class ConversationMessage(Base):
    __tablename__ = "xynassist_conversation_messages"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    conversation_id = Column(
        String(36),
        ForeignKey(
            "xynassist_conversations.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    role = Column(
        String(40),
        nullable=False,
        index=True,
    )

    content = Column(
        Text,
        nullable=False,
    )

    skill = Column(
        String(120),
        nullable=True,
        index=True,
    )

    sequence_number = Column(
        BigInteger,
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
