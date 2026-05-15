from sqlalchemy import Column, Integer, String
from api.db.database import Base


class Church(Base):

    __tablename__ = "churches"

    id = Column(Integer, primary_key=True)

    name = Column(String)

    location = Column(String)