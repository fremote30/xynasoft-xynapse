from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text
)

from sqlalchemy.sql import func

from api.db.database import Base


class MemberProfile(Base):
    __tablename__ = "member_profiles"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )

    # =====================================
    # IDENTITY
    # =====================================
    bio = Column(
        Text,
        default=""
    )

    profile_image = Column(
        String,
        default=""
    )

    favorite_scripture = Column(
        String,
        default=""
    )

    # =====================================
    # LOCATION
    # =====================================
    city = Column(
        String,
        default=""
    )

    state = Column(
        String,
        default=""
    )

    country = Column(
        String,
        default=""
    )

    languages = Column(
        String,
        default=""
    )

    # =====================================
    # FAITH & COMMUNITY
    # =====================================
    church_name = Column(
        String,
        default=""
    )

    ministry_interests = Column(
        Text,
        default=""
    )

    prayer_interests = Column(
        Text,
        default=""
    )

    # =====================================
    # PRIVACY & COMMUNICATION
    # =====================================
    visibility = Column(
        String(length=20),
        nullable=False,
        default="members"
    )

    allow_direct_messages = Column(
        Boolean,
        default=True
    )

    receive_notifications = Column(
        Boolean,
        default=True
    )

    # =====================================
    # PUBLIC LINK
    # =====================================
    slug = Column(
        String,
        unique=True,
        index=True,
        nullable=True
    )

    # =====================================
    # TIMESTAMPS
    # =====================================
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )