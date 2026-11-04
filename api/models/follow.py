from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy.sql import func

from api.db.database import Base


class PastorFollower(Base):
    __tablename__ = "pastor_followers"

    id = Column(Integer, primary_key=True, index=True)

    member_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    pastor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )