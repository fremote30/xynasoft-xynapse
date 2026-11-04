from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint
)

from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from api.db.database import Base


class MemberRecentSermon(Base):
    __tablename__ = "member_recent_sermons"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    member_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    sermon_id = Column(
        Integer,
        ForeignKey(
            "sermons.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    last_opened_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    member = relationship(
        "User"
    )

    sermon = relationship(
        "Sermon"
    )

    __table_args__ = (
        UniqueConstraint(
            "member_id",
            "sermon_id",
            name="uq_member_recent_sermon"
        ),
    )