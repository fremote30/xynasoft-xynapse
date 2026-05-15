from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os


# ================================
# DATABASE URL
# ================================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://xynapse:xynapse_password@db:5432/xynapse"
)

print(f"📦 Connecting to DB: {DATABASE_URL}")


# ================================
# ENGINE
# ================================
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True
)


# ================================
# SESSION
# ================================
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ================================
# BASE MODEL
# ================================
Base = declarative_base()


# ================================
# 🔥 DEPENDENCY (CRITICAL FIX)
# ================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()