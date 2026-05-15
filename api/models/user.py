from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from api.db.database import Base


class User(Base):

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, nullable=False)

    email = Column(String, unique=True, index=True, nullable=False)

    password = Column(String, nullable=False)

    role = Column(String, default="member")

    is_verified = Column(Boolean, default=False)

    church_id = Column(Integer, ForeignKey("churches.id"))

    church = relationship("Church")

    created_at = Column(DateTime, default=datetime.utcnow)

    # =====================================
    # 🔥 RELATIONSHIPS (MUST BE INSIDE CLASS)
    # =====================================

    sermons = relationship(
        "Sermon",
        back_populates="author"
    )

    followers = relationship(
        "PastorMember",
        foreign_keys="PastorMember.pastor_id",
        back_populates="pastor"
    )

    following = relationship(
        "PastorMember",
        foreign_keys="PastorMember.member_id",
        back_populates="member"
    )