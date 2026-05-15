from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from api.db.database import Base


class SermonComment(Base):
    __tablename__ = "sermon_comments"

    # =========================
    # 🔑 CORE FIELDS
    # =========================
    id = Column(Integer, primary_key=True, index=True)

    # 🔥 FIX: ADD FOREIGN KEYS
    sermon_id = Column(Integer, ForeignKey("sermons.id"), nullable=False, index=True)
    pastor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    comment = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # =========================
    # 🔗 RELATIONSHIPS
    # =========================

    # 📖 Link to Sermon
    sermon = relationship(
        "Sermon",
        back_populates="comments"
    )

    # 👤 Link to User (Pastor)
    pastor = relationship(
        "User",
        backref="sermon_comments"
    )