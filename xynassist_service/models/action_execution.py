"""
Durable execution state for XynAssist-owned actions.

A trusted product user plus stable request_id forms the
idempotency boundary. Reusing the request_id with different
action input must fail closed.
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


class ActionExecution(Base):
    __tablename__ = "xynassist_action_executions"

    __table_args__ = (
        UniqueConstraint(
            "product",
            "external_user_id",
            "request_id",
            name=(
                "uq_xynassist_action_execution_"
                "product_user_request"
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

    action_name = Column(
        String(150),
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

    result_json = Column(
        Text,
        nullable=False,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )
