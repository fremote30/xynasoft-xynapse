from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from api.db.database import Base


class PastorMember(Base):

    __tablename__ = "pastor_members"

    id = Column(Integer, primary_key=True, index=True)

    pastor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("pastor_id", "member_id", name="unique_follow"),
    )

    # ✅ FIX: use STRING reference (safest)
    pastor = relationship(
        "User",
        foreign_keys="PastorMember.pastor_id",
        back_populates="followers"
    )

    member = relationship(
        "User",
        foreign_keys="PastorMember.member_id",
        back_populates="following"
    )
