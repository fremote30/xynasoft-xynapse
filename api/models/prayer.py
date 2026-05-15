# api/models/prayer.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from datetime import datetime

# ✅ FIX: Import Base from correct location
from api.db.database import Base  

class Prayer(Base):
    __tablename__ = "prayers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)