"""
Durable idempotency state for XynAssist ministry executions.

A request_id identifies one logical ministry execution for one trusted
product user. Reusing it with different skill input must fail closed.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from xynassist_service.db.database import Base


class MinistryExecution(Base):
    __tablename__ = "xynassist_ministry_executions"

    __table_args__ = (
        UniqueConstraint(
            "product",
            "external_user_id",
            "request_id",
            name=(
                "uq_xynassist_ministry_execution_"
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

    skill = Column(
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
        nullable=True,
    )

    error_code = Column(
        String(120),
        nullable=True,
    )

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
