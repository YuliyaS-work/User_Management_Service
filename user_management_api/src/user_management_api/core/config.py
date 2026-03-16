"""
Application configuration settings.

Defines global constants such as application name, debug mode,
and database connection URL.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Global application configuration settings."""
    APP_NAME: str = "user_management_api"
    DEBUG: bool = True
    DATABASE_URL: str = os.getenv("DATABASE_URL")