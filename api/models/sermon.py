from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from api.db.database import Base


class Sermon(Base):

    __tablename__ = "sermons"

    # =========================
    # 🔑 CORE FIELDS
    # =========================
    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)
    content = Column(Text)

    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    is_public = Column(Integer, default=1)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # =========================
    # 📊 ANALYTICS (DASHBOARD)
    # =========================
    views = Column(Integer, default=0)     # 🔥 number of reads
    shares = Column(Integer, default=0)    # 🔥 quick count (fast access)

    # =========================
    # 🔗 RELATIONSHIPS
    # =========================

    # 👤 Author (Pastor)
    author = relationship(
        "User",
        back_populates="sermons"
    )

    # 🔁 Shared sermons (for collaboration system)
    shared_sermons = relationship(
        "SharedSermon",
        back_populates="sermon",
        cascade="all, delete-orphan"
    )

    # 🧠 FUTURE (optional but recommended)
    # This allows expansion later without refactor
    comments = relationship(
        "SermonComment",
        back_populates="sermon",
        cascade="all, delete-orphan"
    )