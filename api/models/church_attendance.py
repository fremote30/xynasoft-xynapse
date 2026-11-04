"""
XynaFaith V2 church attendance domain.

Attendance is recorded against a ChurchEvent and ChurchMembership so
participation always remains inside the correct Church Space.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import relationship

from api.db.database import Base


ATTENDANCE_STATUS_PRESENT = "present"
ATTENDANCE_STATUS_ABSENT = "absent"
ATTENDANCE_STATUS_EXCUSED = "excused"

ATTENDANCE_STATUSES = frozenset(
    {
        ATTENDANCE_STATUS_PRESENT,
        ATTENDANCE_STATUS_ABSENT,
        ATTENDANCE_STATUS_EXCUSED,
    }
)


class ChurchAttendanceRecord(Base):
    __tablename__ = "church_attendance_records"

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "church_membership_id",
            name="uq_church_attendance_event_membership",
        ),
    )

    id = Column(Integer, primary_key=True)

    event_id = Column(
        Integer,
        ForeignKey("church_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    church_membership_id = Column(
        Integer,
        ForeignKey("church_memberships.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    status = Column(
        String(32),
        nullable=False,
        default=ATTENDANCE_STATUS_PRESENT,
        server_default=ATTENDANCE_STATUS_PRESENT,
    )

    recorded_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    checked_in_at = Column(DateTime, nullable=True)

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

    event = relationship(
        "ChurchEvent",
        back_populates="attendance_records",
    )

    church_membership = relationship(
        "ChurchMembership",
        back_populates="attendance_records",
    )

    recorded_by = relationship(
        "User",
        foreign_keys=[recorded_by_user_id],
    )
