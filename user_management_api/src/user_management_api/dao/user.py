"""
Data Access Object for user-related database operations.
"""

from .base import BaseDAO
from src.user_management_api.models import User

class UserDAO(BaseDAO):
    model = User