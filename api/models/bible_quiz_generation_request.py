"""Durable identity and lifecycle for AI Bible Quiz requests."""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)

from api.db.database import Base


class BibleQuizGenerationRequest(Base):
    __tablename__ = "bible_quiz_generation_requests"

    request_id = Column(
        String(128),
        primary_key=True,
    )

    church_id = Column(
        Integer,
        ForeignKey("churches.id"),
        nullable=False,
        index=True,
    )

    creator_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    input_hash = Column(
        String(64),
        nullable=False,
    )

    status = Column(
        String(20),
        nullable=False,
        default="pending",
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(
            tzinfo=None
        ),
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc).replace(
            tzinfo=None
        ),
        onupdate=lambda: datetime.now(timezone.utc).replace(
            tzinfo=None
        ),
    )
