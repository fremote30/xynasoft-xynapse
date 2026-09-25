"""
XynaFaith V2 Church Space announcements.
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


ANNOUNCEMENT_STATUS_DRAFT = "draft"
ANNOUNCEMENT_STATUS_PUBLISHED = "published"
ANNOUNCEMENT_STATUS_ARCHIVED = "archived"

ANNOUNCEMENT_STATUSES = frozenset(
    {
        ANNOUNCEMENT_STATUS_DRAFT,
        ANNOUNCEMENT_STATUS_PUBLISHED,
        ANNOUNCEMENT_STATUS_ARCHIVED,
    }
)


class ChurchAnnouncement(Base):
    __tablename__ = "church_announcements"

    __table_args__ = (
        Index(
            "ix_church_announcements_church_status",
            "church_id",
            "status",
        ),
        Index(
            "ix_church_announcements_church_published",
            "church_id",
            "published_at",
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

    author_user_id = Column(
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

    body = Column(
        Text,
        nullable=False,
    )

    status = Column(
        String(32),
        nullable=False,
        default=ANNOUNCEMENT_STATUS_DRAFT,
        server_default=ANNOUNCEMENT_STATUS_DRAFT,
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
        back_populates="announcements",
    )

    author = relationship(
        "User",
        foreign_keys=[author_user_id],
    )
