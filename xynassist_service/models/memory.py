"""
Persistent XynAssist user memory model.

Ordinary Xyniva memory stores selected durable context useful across
conversations. Sensitive pastoral-care records belong in protected
domain storage and must not be stored here.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    String,
    Text,
    UniqueConstraint,
    func,
)

from xynassist_service.db.database import Base


class Memory(Base):
    __tablename__ = "xynassist_memories"

    __table_args__ = (
        UniqueConstraint(
            "product",
            "external_user_id",
            "memory_type",
            "key",
            name="uq_xynassist_memory_owner_type_key",
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

    memory_type = Column(
        String(80),
        nullable=False,
        index=True,
    )

    key = Column(
        String(160),
        nullable=False,
    )

    value = Column(
        Text,
        nullable=False,
    )

    source = Column(
        String(80),
        nullable=False,
        default="explicit_user",
        server_default="explicit_user",
        index=True,
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

    last_used_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
