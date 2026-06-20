from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from api.db.database import Base


class Sermon(Base):

    __tablename__ = "sermons"

    # =====================================
    # 🔑 PRIMARY KEY
    # =====================================
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # =====================================
    # 📝 TITLE
    # =====================================
    title = Column(
        String,
        nullable=False,
        default="Untitled Sermon"
    )

    # =====================================
    # 📖 SCRIPTURE
    # =====================================
    scripture = Column(
        String,
        nullable=True
    )

    # =====================================
    # 🧠 SERMON CONTENT
    # =====================================
    content = Column(
        Text,
        nullable=True
    )

    # =====================================
    # 🧠 FUTURE STRUCTURED JSON STORAGE
    # =====================================
    sermon_data = Column(
        JSONB,
        nullable=True
    )

    # =====================================
    # 👤 AUTHOR
    # =====================================
    author_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    # =====================================
    # 🌍 VISIBILITY
    # =====================================
    is_public = Column(
        Integer,
        default=1
    )

    # =====================================
    # 🕒 TIMESTAMPS
    # =====================================
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # =====================================
    # 📊 ANALYTICS
    # =====================================
    views = Column(
        Integer,
        default=0
    )

    shares = Column(
        Integer,
        default=0
    )

    # =====================================
    # 🔗 RELATIONSHIPS
    # =====================================

    author = relationship(
        "User",
        back_populates="sermons"
    )

    shared_sermons = relationship(
        "SharedSermon",
        back_populates="sermon",
        cascade="all, delete-orphan"
    )

    comments = relationship(
        "SermonComment",
        back_populates="sermon",
        cascade="all, delete-orphan"
    )