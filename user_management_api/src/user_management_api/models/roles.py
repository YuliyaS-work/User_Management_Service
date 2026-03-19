"""
SQLAlchemy model for the Role entity.

Contains the Role class mapped to the roles table.
"""
import enum
from typing import TYPE_CHECKING

from sqlalchemy import Integer, Enum
from sqlalchemy.orm import mapped_column, Mapped, relationship

from .base import Base
from .assotiations import user_role


if TYPE_CHECKING:
    from .users import User

class StatusRole(enum.Enum):
    """Model for choice of role value."""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


class Role(Base):
    """SQLAlchemy model for the groups table."""
    __tablename__ = "roles"

    id: Mapped[int]= mapped_column(Integer, primary_key=True)
    role_name: Mapped[StatusRole] = mapped_column(
        Enum(StatusRole, native_enum=False, name="status_role"),
        nullable = False,
        unique=True
    )
    users: Mapped[list["User"]] = relationship(
       secondary=user_role,
       back_populates="roles"
    )