from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Text
)

from sqlalchemy.orm import relationship

from datetime import datetime

# ✅ CORRECT BASE IMPORT
from api.db.database import Base


class Prayer(Base):

    __tablename__ = "prayers"

    # =========================
    # CORE
    # =========================
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # =========================
    # USER
    # =========================
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )

    user_name = Column(
        String,
        nullable=False
    )

    # =========================
    # PRAYER MESSAGE
    # =========================
    message = Column(
        Text,
        nullable=False
    )

    # =========================
    # TIMESTAMP
    # =========================
    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        index=True
    )

    # =========================
    # RELATIONSHIP
    # =========================
    user = relationship(
        "User"
    )