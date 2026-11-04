"""Private pastoral care notes.

These records are intentionally separate from Prayer Wall comments,
Xyniva conversation memory, and member-visible prayer content.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, Text, text
from sqlalchemy.orm import relationship

from api.db.database import Base


class PastoralCareNote(Base):
    __tablename__ = "pastoral_care_notes"

    __table_args__ = (
        Index(
            "ix_pastoral_care_notes_church_case",
            "church_id",
            "case_id",
        ),
    )

    id = Column(Integer, primary_key=True)

    case_id = Column(
        Integer,
        ForeignKey("pastoral_care_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    church_id = Column(
        Integer,
        ForeignKey("churches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    author_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    body = Column(Text, nullable=False)

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

    case = relationship(
        "PastoralCareCase",
        back_populates="notes",
    )

    author = relationship(
        "User",
        foreign_keys=[author_user_id],
    )
