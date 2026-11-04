"""
Immutable factual ledger of XynAssist model-provider executions.

Each row represents one actual provider execution for which XynAssist
received provider/model usage telemetry. Logical request identity is
retained for correlation but is deliberately not unique because lease
recovery may legitimately execute the provider more than once.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    func,
)

from xynassist_service.db.database import Base


class AIExecution(Base):
    __tablename__ = "xynassist_ai_executions"

    id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
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

    request_id = Column(
        String(36),
        nullable=False,
        index=True,
    )

    operation = Column(
        String(150),
        nullable=False,
        index=True,
    )

    provider = Column(
        String(80),
        nullable=False,
        index=True,
    )

    model = Column(
        String(150),
        nullable=False,
        index=True,
    )

    input_tokens = Column(
        Integer,
        nullable=True,
    )

    output_tokens = Column(
        Integer,
        nullable=True,
    )

    attempt_number = Column(
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
