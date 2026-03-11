"""
Assotiation tables for many-to-many relationship between classes.
"""

from sqlalchemy import ForeignKey, Table, Column

from .base import Base


# Assotiation tables for M:M relashionship between the User and the Role classes
user_role = Table(
    "user_role",
    Base.metadata,
    Column("user_id", ForeignKey("users.id"), primary_key=True),
    Column("role_id", ForeignKey("roles.id"), primary_key=True)
)