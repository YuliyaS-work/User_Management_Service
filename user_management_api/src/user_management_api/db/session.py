"""
Database configuration and session management.

Defines SQLAlchemy engine, session factory, and dependency for FastAPI.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.user_management_api.core.config import settings


engine = create_async_engine(settings.database_url, echo=True,)

AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a database session for FastAPI dependency injection."""
    async with AsyncSessionLocal() as session:
        yield session