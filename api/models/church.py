from sqlalchemy import Column, Integer, String, Boolean
from api.db.database import Base

class Church(Base):

    __tablename__ = "churches"

    id = Column(Integer, primary_key=True)

    name = Column(String, nullable=False)

    location = Column(String)

    denomination = Column(String)

    country = Column(String)

    city = Column(String)

    is_featured = Column(Boolean, default=False)

    is_verified = Column(Boolean, default=False)