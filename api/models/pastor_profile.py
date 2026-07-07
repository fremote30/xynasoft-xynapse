from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    ForeignKey,
    DateTime,
    Boolean
)

from sqlalchemy.sql import func

from api.db.database import Base


class PastorProfile(Base):

    __tablename__ = "pastor_profiles"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False
    )

    # Basic information
    bio = Column(Text, default="")
    mission_statement = Column(Text, default="")
    church_name = Column(String, default="")
    church_logo = Column(String, default="")
    church_size = Column(String, default="")
    ministry_focus = Column(String, default="")
    specialties = Column(Text, default="")
    denomination = Column(String, default="")
    years_in_ministry = Column(Integer, default=0)
    ordination_year = Column(Integer, default=0)

    # Location
    location = Column(String, default="")
    city = Column(String, default="")
    state = Column(String, default="")
    country = Column(String, default="")
    time_zone = Column(String, default="")

    # Contact
    website = Column(String, default="")
    phone = Column(String, default="")
    email_public = Column(String, default="")

    # Social media
    facebook = Column(String, default="")
    youtube = Column(String, default="")
    instagram = Column(String, default="")
    twitter = Column(String, default="")

    # Media
    profile_image = Column(String, default="")
    cover_image = Column(String, default="")

    # Ministry
    favorite_scripture = Column(String, default="")
    languages = Column(String, default="")
    service_times = Column(String, default="")

    # Settings
    accepts_prayer_requests = Column(Boolean, default=True)
    allow_direct_messages = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_public = Column(Boolean, default=True)
    visibility = Column(String, default="public")
    
    # Public profile URL
    slug = Column(String, unique=True, index=True, nullable=True)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )