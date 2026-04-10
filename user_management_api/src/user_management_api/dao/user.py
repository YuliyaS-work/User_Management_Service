"""
Data Access Object for user-related database operations.
"""
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select

from .base import BaseDAO
from src.user_management_api.models import User, Role
from .role import RoleDAO
from ..models.assotiations import user_role
from ..models.roles import StatusRole


class UserDAO(BaseDAO):
    model = User


    @classmethod
    async def add(cls, db: AsyncSession, **values):
         user = await super().add(db, **values)

         default_role = await RoleDAO.find_one_or_none(
             db,
             Role.role_name == StatusRole.USER.value
         )

         await db.execute(insert(user_role).values(
             user_id = user.id,
             role_id=default_role.id
         )
         )

         return user

    @classmethod
    async def find_one_or_none_with_related_data(cls, db: AsyncSession, where=None, **filters) -> User | None:
        """
        Find a single record matching the filter or/and the condition or return None.
        """
        query = select(cls.model).options(selectinload(cls.model.roles), selectinload(cls.model.group))

        if where is not None:
            query = query.where(where)

        if filters:
            query = query.filter_by(**filters)

        result = await db.execute(query)
        return result.scalar_one_or_none()



    @classmethod
    async def get_all(cls, db: AsyncSession, where=None):
        query = select(cls.model).options(selectinload(cls.model.roles), selectinload(cls.model.group))

        if where is not None:
            query = query.where(where)

        result = await db.execute(query)
        return result.scalars().all()