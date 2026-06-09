from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey
)

from sqlalchemy.orm import relationship

from datetime import datetime

from api.db.database import Base
from sqlalchemy.dialects.postgresql import JSONB

class Sermon(Base):

    __tablename__ = "sermons"

    # =====================================
    # 📝 TITLE
    # =====================================
    title = Column(
        String,
        nullable=False,
        default="Untitled Sermon"
    )

    # =====================================
    # 📖 SCRIPTURE (NEW)
    # =====================================
    scripture = Column(
        String,
        nullable=True
    )

    # =====================================
    # 🔑 CORE FIELDS
    # =====================================
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # =====================================
    # 🧠 STRUCTURED SERMON JSON
    # STORES FULL JSON STRING
    # =====================================
    content = Column(
        Text,
        nullable=True
    )
  
    # =====================================
    # 🧠 STRUCTURED SERMON JSON
    # FUTURE-PROOF STORAGE
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

    #updated_at = Column(
       # DateTime,
        #default=datetime.utcnow,
        #onupdate=datetime.utcnow
    #)

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

    # 👤 AUTHOR RELATIONSHIP
    author = relationship(
        "User",
        back_populates="sermons"
    )

    # 🔁 SHARED SERMONS
    shared_sermons = relationship(
        "SharedSermon",
        back_populates="sermon",
        cascade="all, delete-orphan"
    )

    # 💬 COMMENTS
    comments = relationship(
        "SermonComment",
        back_populates="sermon",
        cascade="all, delete-orphan"
    )