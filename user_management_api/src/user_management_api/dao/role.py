"""
Data Access Object for group-related database operations.
"""

from .base import BaseDAO
from src.user_management_api.models import Role

class RoleDAO(BaseDAO[Role]):
    model = Role