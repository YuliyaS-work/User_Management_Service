import logging
from datetime import timedelta

from .redis_config import r
from src.user_management_api.core.security import get_token_hash

# Create a module specific logger
logger = logging.getLogger(__name__)


async def delete_refresh_token_from_redis(user_id: str, jti: str) -> None:
    """
    Delete refresh token hash and indicate jti of the refresh token is "revoked".
    """
    logger.info(f"Start: deleting refresh token from redis for user ID={user_id}, jti={jti}")

    try:
        await r.delete(f"refresh_token:{user_id}")
        ttl = timedelta(days=30)
        await r.setex(f"revoked_token:{user_id}:{jti}", int(ttl.total_seconds()), "true")
        logger.info(f"Success: refresh token was deleted from redis for user ID={user_id}")
    except Exception as e:
        logger.warning(f"Redis error: {e}")
        raise


async def save_refresh_token_to_redis(refresh_token: str, jti: str, user_id: str) -> None:
    """
    Save refresh token hash to redis.
    """
    logger.info(f"Start: saving refresh token to redis for user ID={user_id}, jti={jti}")

    try:
        token_hash = get_token_hash(refresh_token)
        ttl = timedelta(days=30)
        await r.setex(f"refresh_token:{user_id}", int(ttl.total_seconds()), token_hash)
        logger.info(f"Success: refresh token was saved to redis for user ID={user_id}")

    except Exception as e:
        logger.warning(f"Redis error: {e}")
        raise
