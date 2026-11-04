from sqlalchemy import Column, Integer, ForeignKey, Text, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from api.db.database import Base


class SharedSermon(Base):
    __tablename__ = "shared_sermons"

    # =========================
    # 🔑 CORE FIELDS
    # =========================
    id = Column(Integer, primary_key=True, index=True)

    sermon_id = Column(Integer, ForeignKey("sermons.id"), nullable=False, index=True)

    from_pastor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    to_pastor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    comment = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # =========================
    # 🔗 RELATIONSHIPS
    # =========================

    # 📖 Linked Sermon
    sermon = relationship(
        "Sermon",
        back_populates="shared_sermons"
    )

    # 👤 Sender (Pastor)
    from_pastor = relationship(
        "User",
        foreign_keys=[from_pastor_id],
        backref="sent_sermons"
    )

    # 👤 Receiver (Pastor)
    to_pastor = relationship(
        "User",
        foreign_keys=[to_pastor_id],
        backref="received_sermons"
    )