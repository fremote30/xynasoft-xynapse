from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)

from api.db.database import Base


class PushDeviceToken(Base):
    """
    Registered mobile device capable of receiving push notifications.

    A user may own multiple devices, while a physical/app installation
    token must remain unique.
    """

    __tablename__ = "push_device_tokens"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    token = Column(
        String,
        nullable=False,
        unique=True,
        index=True,
    )

    platform = Column(
        String(20),
        nullable=False,
    )

    is_active = Column(
        Boolean,
        nullable=False,
        default=True,
    )

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
