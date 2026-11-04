"""
XynaFaith V2 Church Space reading plans.
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


READING_PLAN_STATUS_DRAFT = "draft"
READING_PLAN_STATUS_PUBLISHED = "published"
READING_PLAN_STATUS_ARCHIVED = "archived"

READING_PLAN_STATUSES = frozenset(
    {
        READING_PLAN_STATUS_DRAFT,
        READING_PLAN_STATUS_PUBLISHED,
        READING_PLAN_STATUS_ARCHIVED,
    }
)


class ReadingPlan(Base):
    __tablename__ = "reading_plans"

    id = Column(Integer, primary_key=True)

    church_id = Column(
        Integer,
        ForeignKey("churches.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    creator_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title = Column(
        String(200),
        nullable=False,
    )

    description = Column(
        Text,
        nullable=True,
    )

    duration_days = Column(
        Integer,
        nullable=False,
    )

    status = Column(
        String(32),
        nullable=False,
        default=READING_PLAN_STATUS_DRAFT,
        server_default=READING_PLAN_STATUS_DRAFT,
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
        back_populates="reading_plans",
    )

    days = relationship(
        "ReadingPlanDay",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="ReadingPlanDay.day_number",
    )

    enrollments = relationship(
        "MemberReadingPlan",
        back_populates="plan",
    )

    __table_args__ = (
        Index(
            "ix_reading_plans_church_status",
            "church_id",
            "status",
        ),
        Index(
            "ix_reading_plans_church_published",
            "church_id",
            "published_at",
        ),
    )


class ReadingPlanDay(Base):
    __tablename__ = "reading_plan_days"

    id = Column(Integer, primary_key=True)

    plan_id = Column(
        Integer,
        ForeignKey("reading_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    day_number = Column(
        Integer,
        nullable=False,
    )

    title = Column(
        String(200),
        nullable=True,
    )

    scripture = Column(
        String(500),
        nullable=False,
    )

    reflection = Column(
        Text,
        nullable=True,
    )

    prompt = Column(
        Text,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
    )

    plan = relationship(
        "ReadingPlan",
        back_populates="days",
    )

    progress = relationship(
        "MemberReadingProgress",
        back_populates="day",
        passive_deletes=True,
    )

    __table_args__ = (
        Index(
            "ux_reading_plan_day_number",
            "plan_id",
            "day_number",
            unique=True,
        ),
    )
