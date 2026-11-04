"""Pastoral care activity history.

Activity records describe workflow changes without copying private
pastoral-care note contents into the audit stream.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.orm import relationship

from api.db.database import Base


PASTORAL_CARE_ACTIVITY_TYPES = {
    "case_created",
    "assigned",
    "reassigned",
    "status_changed",
    "follow_up_scheduled",
    "note_added",
    "resolved",
    "closed",
}


class PastoralCareActivity(Base):
    __tablename__ = "pastoral_care_activities"

    __table_args__ = (
        Index(
            "ix_pastoral_care_activities_church_case",
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

    actor_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    activity_type = Column(
        String(64),
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
    )

    case = relationship(
        "PastoralCareCase",
        back_populates="activities",
    )

    actor = relationship(
        "User",
        foreign_keys=[actor_user_id],
    )
