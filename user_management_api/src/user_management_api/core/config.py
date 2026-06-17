"""
Application configuration settings.

Defines global constants such as application name, debug mode,
and database connection URL.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str
    bucket_name: str

    rabbitmq_url: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()