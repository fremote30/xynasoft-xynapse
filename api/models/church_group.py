"""
XynaFaith V2 Church Groups & Ministries domain.

Groups are subordinate to a Church Space. Group membership is bound
to ChurchMembership so a user cannot participate in a group without
belonging to the owning church.
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from api.db.database import Base


GROUP_TYPE_MINISTRY = "ministry"
GROUP_TYPE_SMALL_GROUP = "small_group"
GROUP_TYPE_TEAM = "team"
GROUP_TYPE_CLASS = "class"
GROUP_TYPE_OTHER = "other"

GROUP_TYPES = frozenset(
    {
        GROUP_TYPE_MINISTRY,
        GROUP_TYPE_SMALL_GROUP,
        GROUP_TYPE_TEAM,
        GROUP_TYPE_CLASS,
        GROUP_TYPE_OTHER,
    }
)

GROUP_STATUS_ACTIVE = "active"
GROUP_STATUS_INACTIVE = "inactive"
GROUP_STATUS_ARCHIVED = "archived"

GROUP_STATUSES = frozenset(
    {
        GROUP_STATUS_ACTIVE,
        GROUP_STATUS_INACTIVE,
        GROUP_STATUS_ARCHIVED,
    }
)

GROUP_MEMBER_ROLE_LEADER = "leader"
GROUP_MEMBER_ROLE_CO_LEADER = "co_leader"
GROUP_MEMBER_ROLE_MEMBER = "member"

GROUP_MEMBER_ROLES = frozenset(
    {
        GROUP_MEMBER_ROLE_LEADER,
        GROUP_MEMBER_ROLE_CO_LEADER,
        GROUP_MEMBER_ROLE_MEMBER,
    }
)

GROUP_MEMBER_STATUS_INVITED = "invited"
GROUP_MEMBER_STATUS_ACTIVE = "active"
GROUP_MEMBER_STATUS_LEFT = "left"

GROUP_MEMBER_STATUSES = frozenset(
    {
        GROUP_MEMBER_STATUS_INVITED,
        GROUP_MEMBER_STATUS_ACTIVE,
        GROUP_MEMBER_STATUS_LEFT,
    }
)


class ChurchGroup(Base):
    __tablename__ = "church_groups"

    __table_args__ = (
        UniqueConstraint(
            "church_id",
            "name",
            name="uq_church_groups_church_name",
        ),
    )

    id = Column(Integer, primary_key=True)

    church_id = Column(
        Integer,
        ForeignKey("churches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name = Column(String(200), nullable=False)
    description = Column(Text)
    group_type = Column(String(32), nullable=False)
    status = Column(
        String(32),
        nullable=False,
        default=GROUP_STATUS_ACTIVE,
        server_default=GROUP_STATUS_ACTIVE,
    )

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    church = relationship("Church", back_populates="groups")

    memberships = relationship(
        "ChurchGroupMembership",
        back_populates="group",
        cascade="all, delete-orphan",
    )

    service_assignments = relationship(
        "ChurchServiceAssignment",
        back_populates="group",
    )


class ChurchGroupMembership(Base):
    __tablename__ = "church_group_memberships"

    __table_args__ = (
        UniqueConstraint(
            "group_id",
            "church_membership_id",
            name="uq_church_group_memberships_group_membership",
        ),
    )

    id = Column(Integer, primary_key=True)

    group_id = Column(
        Integer,
        ForeignKey("church_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    church_membership_id = Column(
        Integer,
        ForeignKey("church_memberships.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    role = Column(
        String(32),
        nullable=False,
        default=GROUP_MEMBER_ROLE_MEMBER,
        server_default=GROUP_MEMBER_ROLE_MEMBER,
    )

    status = Column(
        String(32),
        nullable=False,
        default=GROUP_MEMBER_STATUS_ACTIVE,
        server_default=GROUP_MEMBER_STATUS_ACTIVE,
    )

    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    group = relationship(
        "ChurchGroup",
        back_populates="memberships",
    )

    church_membership = relationship(
        "ChurchMembership",
        back_populates="group_memberships",
    )
