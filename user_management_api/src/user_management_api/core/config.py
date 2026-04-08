"""
Application configuration settings.

Defines global constants such as application name, debug mode,
and database connection URL.
"""
import aioboto3
import boto3
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

    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str
    bucket_name: str

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

r = Redis(
    host=settings.redis_host,
    password=settings.redis_password,
    port=settings.redis_port,
    decode_responses=True
    )

s3_session = aioboto3.Session(
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
)