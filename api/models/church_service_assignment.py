"""
XynaFaith V2 volunteer and service-team assignment domain.

A service assignment schedules a ChurchMembership to serve at a
ChurchEvent through a ChurchGroup whose group type is team.
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


SERVICE_ASSIGNMENT_STATUS_ASSIGNED = "assigned"
SERVICE_ASSIGNMENT_STATUS_CONFIRMED = "confirmed"
SERVICE_ASSIGNMENT_STATUS_DECLINED = "declined"
SERVICE_ASSIGNMENT_STATUS_COMPLETED = "completed"
SERVICE_ASSIGNMENT_STATUS_CANCELLED = "cancelled"

SERVICE_ASSIGNMENT_STATUSES = frozenset(
    {
        SERVICE_ASSIGNMENT_STATUS_ASSIGNED,
        SERVICE_ASSIGNMENT_STATUS_CONFIRMED,
        SERVICE_ASSIGNMENT_STATUS_DECLINED,
        SERVICE_ASSIGNMENT_STATUS_COMPLETED,
        SERVICE_ASSIGNMENT_STATUS_CANCELLED,
    }
)


class ChurchServiceAssignment(Base):
    __tablename__ = "church_service_assignments"

    __table_args__ = (
        UniqueConstraint(
            "event_id",
            "group_id",
            "church_membership_id",
            "service_role",
            name="uq_church_service_assignment",
        ),
    )

    id = Column(Integer, primary_key=True)

    event_id = Column(
        Integer,
        ForeignKey("church_events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    group_id = Column(
        Integer,
        ForeignKey("church_groups.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    church_membership_id = Column(
        Integer,
        ForeignKey("church_memberships.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    service_role = Column(
        String(120),
        nullable=False,
    )

    status = Column(
        String(32),
        nullable=False,
        default=SERVICE_ASSIGNMENT_STATUS_ASSIGNED,
        server_default=SERVICE_ASSIGNMENT_STATUS_ASSIGNED,
    )

    assigned_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
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

    event = relationship(
        "ChurchEvent",
        back_populates="service_assignments",
    )

    group = relationship(
        "ChurchGroup",
        back_populates="service_assignments",
    )

    church_membership = relationship(
        "ChurchMembership",
        back_populates="service_assignments",
    )

    assigned_by = relationship(
        "User",
        foreign_keys=[assigned_by_user_id],
    )
