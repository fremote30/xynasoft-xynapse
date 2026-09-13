"""
XynaFaith V2 church membership domain.

A membership binds one XynaFaith identity to one Church Space.
Church-scoped authorization belongs to this relationship rather
than to the user's legacy global role.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Index,
    text,
)
from sqlalchemy.orm import relationship

from api.db.database import Base


class ChurchMembership(Base):
    __tablename__ = "church_memberships"

    __table_args__ = (
        UniqueConstraint(
            "church_id",
            "user_id",
            name="uq_church_memberships_church_user",
        ),
        Index(
            "uq_church_memberships_primary_user",
            "user_id",
            unique=True,
            postgresql_where=text("is_primary = true"),
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
    )

    church_id = Column(
        Integer,
        ForeignKey(
            "churches.id",
            ondelete="CASCADE",
        ),
        nullable=False,
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

    role = Column(
        String(32),
        nullable=False,
        default="member",
        server_default="member",
    )

    status = Column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
    )

    is_primary = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    joined_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
    )

    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
        onupdate=datetime.utcnow,
    )

    church = relationship(
        "Church",
        back_populates="memberships",
    )

    user = relationship(
        "User",
        back_populates="church_memberships",
    )
