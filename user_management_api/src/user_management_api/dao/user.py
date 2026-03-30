"""
Data Access Object for user-related database operations.
"""
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

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