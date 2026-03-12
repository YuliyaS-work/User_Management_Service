"""
Database configuration and session management.

Defines SQLAlchemy engine, session factory, and dependency for FastAPI.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.user_management_api.core import config
# from src.user_management_api.models.base import Base

engine = create_engine(config.Settings.DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Base.metadata.create_all(bind=engine)


def get_session():
    """Provide a database session for FastAPI dependency injection."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()