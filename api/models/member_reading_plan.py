from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from api.db.database import Base


class MemberReadingPlan(Base):
    __tablename__ = "member_reading_plans"

    id = Column(Integer, primary_key=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    plan_id = Column(
        Integer,
        ForeignKey("reading_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(
        String(32),
        nullable=False,
        default="active",
    )

    started_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    completed_at = Column(DateTime, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    plan = relationship(
        "ReadingPlan",
        back_populates="enrollments",
    )

    progress = relationship(
        "MemberReadingProgress",
        back_populates="enrollment",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index(
            "ux_member_reading_plan",
            "user_id",
            "plan_id",
            unique=True,
        ),
    )


class MemberReadingProgress(Base):
    __tablename__ = "member_reading_progress"

    id = Column(Integer, primary_key=True)

    enrollment_id = Column(
        Integer,
        ForeignKey(
            "member_reading_plans.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    day_id = Column(
        Integer,
        ForeignKey("reading_plan_days.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    completed_at = Column(DateTime, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    enrollment = relationship(
        "MemberReadingPlan",
        back_populates="progress",
    )

    day = relationship(
        "ReadingPlanDay",
        back_populates="progress",
    )

    __table_args__ = (
        Index(
            "ux_member_reading_progress_day",
            "enrollment_id",
            "day_id",
            unique=True,
        ),
    )
