"""
Base class for Data Access Objects.
"""

from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.models import User


class BaseDAO:
    model=None

    @classmethod
    async def find_one_or_none(cls, db: AsyncSession, where=None,  **filters) -> User | None:
        """
        Find a single record matching the filter or/and the condition or return None.
        """
        query = select(cls.model)

        if where is not None:
            query = query.where(where)

        if filters:
            query = query.filter_by(**filters)

        result = await db.execute(query)
        return result.scalar_one_or_none()

    @classmethod
    async def add(cls, db: AsyncSession, **values) -> User:
        """
        Add a new instance to the session without commiting.
        """
        new_instance = cls.model(**values)
        db.add(new_instance)
        await db.flush()
        return new_instance