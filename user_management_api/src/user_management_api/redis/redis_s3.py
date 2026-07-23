import logging
from datetime import timedelta

from src.user_management_api.redis.redis_config import r

# Create a module specific logger
logger = logging.getLogger(__name__)

async def save_presigned_url_to_redis(presigned_url: str, user_id: str) -> None:
    """
    Save predesign_url to redis.
    """
    logger.info(f"Start: saving presigned url avatar to redis, url={presigned_url}, user ID={user_id}")
    try:
        ttl = timedelta(seconds=3600)
        await r.setex(f"presigned_url:{user_id}", int(ttl.total_seconds()), presigned_url)

        logger.info(f"Success: presigned url avatar was saved to redis, ulr={presigned_url}, user ID={user_id}")
    except Exception as e:
        logger.warning(f"Redis error: {e}")
        pass


async def delete_presigned_url_from_redis(user_id: str) -> None:
    """
    Delete predesign_url from redis.
    """
    logger.info(f"Start: deleting presigned url avatar from redis by user ID={user_id}")

    try:
        await r.delete(f"presigned_url:{user_id}")

        logger.info(f"Success: presigned url avatar was deleted from redis for user ID={user_id}")
    except Exception as e:
        logger.warning(f"Redis error: {e}")
        pass


async def get_presigned_url_from_redis(user_id: str) ->str | None:
    """
    Get predesign_url from redis.
    """
    logger.info(f"Start: fetching presigned url avatar from redis by ID={user_id}")

    try:
        presigned_url: str | None = await r.get(f"presigned_url:{user_id}")

        logger.info("Success: available presigned url avatar was fetched from redis")
        return presigned_url
    except Exception as e:
        logger.warning(f"Redis error: {e}")
        return None