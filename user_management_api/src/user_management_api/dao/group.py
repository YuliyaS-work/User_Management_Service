"""
Data Access Object for group-related database operations.
"""

from .base import BaseDAO
from src.user_management_api.models import Group

class GroupDAO(BaseDAO):
    model = Group