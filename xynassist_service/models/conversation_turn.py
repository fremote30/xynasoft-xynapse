"""
Durable idempotency state for XynAssist conversation turns.

A request_id identifies one logical AI turn for one trusted
product user. Reusing it with different input must fail
rather than execute another model request.
"""

from __future__ import annotations

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from xynassist_service.db.database import Base


class ConversationTurn(Base):
    __tablename__ = "xynassist_conversation_turns"

    __table_args__ = (
        UniqueConstraint(
            "product",
            "external_user_id",
            "request_id",
            name=(
                "uq_xynassist_turn_"
                "product_user_request"
            ),
        ),
    )

    id = Column(
        String(36),
        primary_key=True,
    )

    product = Column(
        String(80),
        nullable=False,
        index=True,
    )

    external_user_id = Column(
        String(255),
        nullable=False,
        index=True,
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

    request_id = Column(
        String(36),
        nullable=False,
        index=True,
    )

    request_fingerprint = Column(
        String(64),
        nullable=False,
    )

    status = Column(
        String(32),
        nullable=False,
        index=True,
    )

    user_message_id = Column(
        String(36),
        ForeignKey(
            "xynassist_conversation_messages.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    assistant_message_id = Column(
        String(36),
        ForeignKey(
            "xynassist_conversation_messages.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    response_json = Column(
        Text,
        nullable=True,
    )

    error_code = Column(
        String(120),
        nullable=True,
    )

    # Processing leases allow abandoned turns to be recovered while
    # fencing workers that no longer own the current attempt.
    lease_token = Column(
        String(36),
        nullable=True,
    )

    lease_expires_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    attempt_count = Column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
