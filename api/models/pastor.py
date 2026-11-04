from sqlalchemy import Column, Integer, String
from api.db.database import Base

class Pastor(Base):
    __tablename__ = "pastors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)