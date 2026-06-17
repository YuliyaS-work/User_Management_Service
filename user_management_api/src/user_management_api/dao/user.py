"""
Data Access Object for user-related database operations.
"""
import uuid
from typing import Any, Optional, Sequence

from sqlalchemy import insert, delete, ColumnElement, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select

from .base import BaseDAO
from src.user_management_api.models import User, Role
from .role import RoleDAO
from ..models.assotiations import user_role
from ..models.roles import StatusRole
from ..schemas.user import UserFilter, UserPagination


class UserDAO(BaseDAO[User]):
    model = User


    @classmethod
    async def add(cls, db: AsyncSession, **values: Any) -> User:
        user = await super().add(db, **values)

        default_role = await RoleDAO.find_one_or_none(
            db,
            Role.role_name == StatusRole.USER.value
        )

        if default_role is None:
            raise RuntimeError("Default USER role is missing in the database.")

        await db.execute(insert(user_role).values(
            user_id = user.id,
            role_id=default_role.id
        ))

        return user


    @classmethod
    async def find_one_or_none_with_related_data(cls, db: AsyncSession, where: Optional[ColumnElement[bool]]=None, **filters: Any) -> User | None:
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
    async def get_all(
            cls,
            db: AsyncSession,
            pagination: UserPagination,
            role_condition = None,
            user_filter: UserFilter = None
    ) -> tuple[Sequence[User], int]:
        query = select(cls.model)

        if role_condition is not None:
            query = query.where(role_condition)

        if user_filter.name:
            query = query.where(User.name.ilike(f"%{user_filter.name}%"))

        if user_filter.surname:
            query = query.where(User.surname.ilike(f"%{user_filter.surname}%"))

        if user_filter.sort_field and hasattr(cls.model, user_filter.sort_field):
            sorted_column = getattr(cls.model, user_filter.sort_field)
            if user_filter.order_by == "desc":
                query = query.order_by(sorted_column.desc())
            else:
                query = query.order_by(sorted_column.asc())

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total_items = total_result.scalar()

        query =query.limit(pagination.limit).offset(pagination.offset).options(selectinload(cls.model.roles), selectinload(cls.model.group))

        result = await db.execute(query)
        items = result.scalars().all()

        return items, total_items


    @classmethod
    async def patch_by_id(cls, db: AsyncSession, user_id: str, data: dict[str, Any]) -> None:
        """
        Patch a user to the session without commiting.
        """
        user_id_uuid = uuid.UUID(user_id)
        renew_instance = await db.get(cls.model, user_id_uuid)

        for field, value in data.items():
            setattr(renew_instance, field, value)


    @classmethod
    async def update_user_role(cls, db: AsyncSession, user_id: str, roles_id: list[int] ) -> None:
        """
        Update roles for user in user_role table without commiting.
        """
        user_id_uuid = uuid.UUID(user_id)
        await db.execute(
            delete(user_role).where(user_role.c.user_id == user_id_uuid)
        )

        if roles_id is not None:
            await db.execute(
                insert(user_role),
                [{"user_id": user_id_uuid, "role_id": role_id} for role_id in roles_id]
            )

    @classmethod
    async def delete_by_id(cls, db: AsyncSession, user_id: str) -> None:
        """
        Delete a user to the session without commiting.
        """
        user_id_uuid = uuid.UUID(user_id)
        instance = await db.get(cls.model, user_id_uuid)
        await db.delete(instance)
        await db.flush()