"""
Persistent XynAssist conversation model.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    String,
    UniqueConstraint,
    func,
)

from xynassist_service.db.database import Base


class Conversation(Base):
    __tablename__ = "xynassist_conversations"

    __table_args__ = (
        UniqueConstraint(
            "product",
            "external_user_id",
            "id",
            name=(
                "uq_xynassist_conversation_"
                "product_user_id"
            ),
        ),
    )

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    product = Column(
        String(80),
        nullable=False,
        default="xynafaith",
        index=True,
    )

    external_user_id = Column(
        String(255),
        nullable=False,
        index=True,
    )

    title = Column(
        String(255),
        nullable=True,
    )

    status = Column(
        String(40),
        nullable=False,
        default="active",
        server_default="active",
        index=True,
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
