from redis.asyncio import Redis

from src.user_management_api.core.config import settings

r = Redis(
    host=settings.redis_host,
    password=settings.redis_password,
    port=settings.redis_port,
    decode_responses=True
    )