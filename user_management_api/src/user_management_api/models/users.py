"""
SQLAlchemy model for the User entity.

Contains the User class mapped to the users table.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy_utils import PhoneNumberType, EmailType, PhoneNumber
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import mapped_column, Mapped, relationship
from sqlalchemy.dialects.postgresql import UUID

from .base import Base
from .assotiations import user_role


if TYPE_CHECKING:
    from .groups import Group
    from .roles import Role

class User(Base):
    """SQLAlchemy model for the users table."""
    __tablename__ = "users"

    id: Mapped[uuid.UUID]= mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    surname: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone_number: Mapped[Optional[PhoneNumber]] = mapped_column(PhoneNumberType(), nullable=True)
    email: Mapped[str]= mapped_column(EmailType(), nullable=False, unique=True)
    image_s3_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    modified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    group_id: Mapped[int] = mapped_column(ForeignKey("groups.id"), nullable=True)
    group: Mapped["Group"] = relationship(back_populates="users")
    roles: Mapped[list["Role"]] = relationship(
        secondary=user_role,
        back_populates="users"
    )