"""
SQLAlchemy model for the Group entity.

Contains the Group class mapped to the groups table.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import String, DateTime, Integer, func
from sqlalchemy.orm import mapped_column, Mapped, relationship

from .base import Base

if TYPE_CHECKING:
    from .users import User

class Group(Base):
    """SQLAlchemy model for the groups table."""
    __tablename__ = "groups"

    id: Mapped[int]= mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    users: Mapped[list["User"]] = relationship(back_populates="group")