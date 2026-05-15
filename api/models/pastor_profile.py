from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime
)

from sqlalchemy.sql import func

from api.db.database import Base


class PastorProfile(Base):

    __tablename__ = "pastor_profiles"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    bio = Column(
        Text,
        default=""
    )

    church_name = Column(
        String,
        default=""
    )

    ministry_focus = Column(
        String,
        default=""
    )

    location = Column(
        String,
        default=""
    )

    website = Column(
        String,
        default=""
    )

    profile_image = Column(
        String,
        default=""
    )

    cover_image = Column(
        String,
        default=""
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )