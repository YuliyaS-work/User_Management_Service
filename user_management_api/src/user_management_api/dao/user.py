"""
Data Access Object for user-related database operations.
"""
import uuid
from typing import Any

from sqlalchemy import insert, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select

from .base import BaseDAO
from src.user_management_api.models import User, Role
from .role import RoleDAO
from ..models.assotiations import user_role
from ..models.roles import StatusRole


class UserDAO(BaseDAO[User]):
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
    async def get_all(cls, db: AsyncSession, *conditions):
        query = select(cls.model).options(selectinload(cls.model.roles), selectinload(cls.model.group))

        for condition in conditions:
            if condition is not None:
                query = query.where(condition)

        result = await db.execute(query)
        return result.scalars().all()


    @classmethod
    async def patch_by_id(cls, db: AsyncSession, user_id: str, data: dict[str, Any]) -> None:
        """
        Patch a user to the session without commiting.
        """
        user_id = uuid.UUID(user_id)
        renew_instance = await db.get(cls.model, user_id)

        for field, value in data.items():
            setattr(renew_instance, field, value)


    @classmethod
    async def update_user_role(cls, db: AsyncSession, user_id: str, roles_id: list[int] ) -> None:
        """
        Update roles for user in user_role table without commiting.
        """
        user_id = uuid.UUID(user_id)
        await db.execute(
            delete(user_role).where(user_role.c.user_id == user_id)
        )

        if roles_id is not None:
            await db.execute(
                insert(user_role),
                [{"user_id": user_id, "role_id": role_id} for role_id in roles_id]
            )

    @classmethod
    async def delete_by_id(cls, db: AsyncSession, user_id: str) -> None:
        """
        Delete a user to the session without commiting.
        """
        user_id = uuid.UUID(user_id)
        instance = await db.get(cls.model, user_id)
        await db.delete(instance)
        await db.flush()