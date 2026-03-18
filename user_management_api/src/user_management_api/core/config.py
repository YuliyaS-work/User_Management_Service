"""
Application configuration settings.

Defines global constants such as application name, debug mode,
and database connection URL.
"""
import os

import redis
from dotenv import load_dotenv

load_dotenv()

class Settings:
    """Global application configuration settings."""
    APP_NAME: str = "user_management_api"
    DEBUG: bool = True
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    SECRET_KEY: str = os.getenv("SECRET_KEY")
    PRIVATE_KEY_PATH = os.getenv("JWT_PRVK_PATH")
    PUBLIC_KEY_PATH = os.getenv("JWT_PBK_PATH")
    ALGORITHM: str = os.getenv("ALGORITHM")

    r = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        password=os.getenv("REDIS_PASSWORD"),
        port=os.getenv("REDIS_PORT"),
        decode_responses=True
    )