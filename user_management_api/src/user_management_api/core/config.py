"""
Application configuration settings.

Defines global constants such as application name, debug mode,
and database connection URL.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from redis.asyncio import Redis

class Settings(BaseSettings):
    """Global application configuration settings."""
    app_name: str = "user_management_api"
    debug: bool = True
    database_url: str
    secret_key: str
    algorithm: str

    redis_host: str
    redis_port: int
    redis_password: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

r = Redis(
    host=settings.redis_host,
    password=settings.redis_password,
    port=settings.redis_port,
    decode_responses=True
    )