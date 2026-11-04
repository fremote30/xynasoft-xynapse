"""XynaFaith V2 pastoral care case domain."""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import relationship

from api.db.database import Base


PASTORAL_CARE_STATUSES = {
    "open",
    "in_progress",
    "waiting",
    "resolved",
    "closed",
}

PASTORAL_CARE_PRIORITIES = {
    "routine",
    "important",
    "urgent",
}


class PastoralCareCase(Base):
    __tablename__ = "pastoral_care_cases"

    __table_args__ = (
        Index(
            "ix_pastoral_care_cases_church_status",
            "church_id",
            "status",
        ),
        Index(
            "ix_pastoral_care_cases_church_assignee",
            "church_id",
            "assigned_to_user_id",
        ),
        Index(
            "ix_pastoral_care_cases_church_follow_up",
            "church_id",
            "follow_up_at",
        ),
    )

    id = Column(Integer, primary_key=True)

    church_id = Column(
        Integer,
        ForeignKey("churches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    prayer_id = Column(
        Integer,
        ForeignKey("prayers.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    member_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    assigned_to_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status = Column(
        String(32),
        nullable=False,
        default="open",
        server_default="open",
    )

    priority = Column(
        String(32),
        nullable=False,
        default="routine",
        server_default="routine",
    )

    follow_up_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)

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

    church = relationship("Church", back_populates="pastoral_care_cases")
    prayer = relationship("Prayer", back_populates="pastoral_care_case")

    member = relationship(
        "User",
        foreign_keys=[member_user_id],
    )

    assigned_to = relationship(
        "User",
        foreign_keys=[assigned_to_user_id],
    )

    notes = relationship(
        "PastoralCareNote",
        back_populates="case",
        cascade="all, delete-orphan",
    )

    activities = relationship(
        "PastoralCareActivity",
        back_populates="case",
        cascade="all, delete-orphan",
    )
