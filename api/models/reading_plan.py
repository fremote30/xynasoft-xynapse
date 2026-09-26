from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from api.db.database import Base


class ReadingPlan(Base):
    __tablename__ = "reading_plans"

    id = Column(Integer, primary_key=True)

    creator_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    duration_days = Column(Integer, nullable=False)
    status = Column(String(32), nullable=False, default="draft")

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
            "ix_reading_plans_status_created",
            "status",
            "created_at",
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

    day_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=True)
    scripture = Column(String(500), nullable=False)
    reflection = Column(Text, nullable=True)
    prompt = Column(Text, nullable=True)

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    plan = relationship(
        "ReadingPlan",
        back_populates="days",
    )

    progress = relationship(
        "MemberReadingProgress",
        back_populates="day",
    )

    __table_args__ = (
        Index(
            "ux_reading_plan_day_number",
            "plan_id",
            "day_number",
            unique=True,
        ),
    )
