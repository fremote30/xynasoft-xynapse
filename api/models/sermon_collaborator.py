from sqlalchemy import Column, Integer, ForeignKey
from api.db.session import Base

class SermonCollaborator(Base):

    __tablename__ = "sermon_collaborators"

    id = Column(Integer, primary_key=True)

    sermon_id = Column(Integer, ForeignKey("sermons.id"))

    pastor_id = Column(Integer, ForeignKey("pastors.id"))