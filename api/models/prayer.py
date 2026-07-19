from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from api.db.database import Base


class Prayer(Base):
    __tablename__ = "prayers"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user_name = Column(String, nullable=False)

    message = Column(Text, nullable=False)
    category = Column(String, nullable=True, index=True)

    # community | private | mixed
    visibility = Column(String, default="community", index=True)

    status = Column(String, default="still_praying", index=True)
    is_anonymous = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False, index=True)
    is_locked = Column(Boolean, default=False)

    prayer_count = Column(Integer, default=0)
    support_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)

    answered_at = Column(DateTime, nullable=True)

    answer_testimony = Column(Text, nullable=True)
    testimony_shared_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")
    recipients = relationship("PrayerRecipient", cascade="all, delete-orphan")
    reactions = relationship("PrayerReaction", cascade="all, delete-orphan")
    comments = relationship("PrayerComment", cascade="all, delete-orphan")
    bookmarks = relationship("PrayerBookmark", cascade="all, delete-orphan")


class PrayerRecipient(Base):
    __tablename__ = "prayer_recipients"

    id = Column(Integer, primary_key=True, index=True)

    prayer_id = Column(Integer, ForeignKey("prayers.id"), nullable=False, index=True)
    recipient_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # pastor | member | admin
    recipient_role = Column(String, nullable=True, index=True)

    is_read = Column(Boolean, default=False)
    prayed_at = Column(DateTime, nullable=True)
    responded_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    __table_args__ = (
        UniqueConstraint(
            "prayer_id",
            "recipient_user_id",
            name="uq_prayer_recipient_user"
        ),
    )


class PrayerReaction(Base):
    __tablename__ = "prayer_reactions"

    id = Column(Integer, primary_key=True, index=True)
    prayer_id = Column(Integer, ForeignKey("prayers.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reaction_type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "prayer_id",
            "user_id",
            "reaction_type",
            name="uq_prayer_user_reaction"
        ),
    )


class PrayerComment(Base):
    __tablename__ = "prayer_comments"

    id = Column(Integer, primary_key=True, index=True)
    prayer_id = Column(Integer, ForeignKey("prayers.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    user_name = Column(String, nullable=False)

    parent_id = Column(Integer, ForeignKey("prayer_comments.id"), nullable=True)
    comment = Column(Text, nullable=False)

    is_pastor_response = Column(Boolean, default=False)
    is_pinned = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PrayerBookmark(Base):
    __tablename__ = "prayer_bookmarks"

    id = Column(Integer, primary_key=True, index=True)
    prayer_id = Column(Integer, ForeignKey("prayers.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint(
            "prayer_id",
            "user_id",
            name="uq_prayer_user_bookmark"
        ),
    )


class PrayerReport(Base):
    __tablename__ = "prayer_reports"

    id = Column(Integer, primary_key=True, index=True)
    prayer_id = Column(Integer, ForeignKey("prayers.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reason = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PrayerNotification(Base):
    __tablename__ = "prayer_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    prayer_id = Column(Integer, ForeignKey("prayers.id"), nullable=True, index=True)

    notification_type = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)