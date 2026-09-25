"""
XynaFaith V2 Church Space events.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.orm import relationship

from api.db.database import Base


EVENT_STATUS_DRAFT = "draft"
EVENT_STATUS_PUBLISHED = "published"
EVENT_STATUS_CANCELLED = "cancelled"

EVENT_STATUSES = frozenset(
    {
        EVENT_STATUS_DRAFT,
        EVENT_STATUS_PUBLISHED,
        EVENT_STATUS_CANCELLED,
    }
)


class ChurchEvent(Base):
    __tablename__ = "church_events"

    __table_args__ = (
        Index(
            "ix_church_events_church_status",
            "church_id",
            "status",
        ),
        Index(
            "ix_church_events_church_starts",
            "church_id",
            "starts_at",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
    )

    church_id = Column(
        Integer,
        ForeignKey(
            "churches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    created_by_user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="SET NULL",
        ),
        nullable=True,
    )

    title = Column(
        String(200),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    starts_at = Column(
        DateTime,
        nullable=False,
    )

    ends_at = Column(
        DateTime,
        nullable=True,
    )

    location = Column(
        String(255),
        nullable=True,
    )

    event_url = Column(
        String(1000),
        nullable=True,
    )

    status = Column(
        String(32),
        nullable=False,
        default=EVENT_STATUS_DRAFT,
        server_default=EVENT_STATUS_DRAFT,
    )

    published_at = Column(
        DateTime,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
        onupdate=datetime.utcnow,
    )

    church = relationship(
        "Church",
        back_populates="events",
    )

    created_by = relationship(
        "User",
        foreign_keys=[created_by_user_id],
    )
