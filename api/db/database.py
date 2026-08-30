from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os


# ================================
# DATABASE URL
# ================================
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required"
    )

print("📦 Database configuration loaded")


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