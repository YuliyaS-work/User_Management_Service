import json
import logging
from datetime import timedelta
from typing import Any



from .redis_config import r

# Create a module specific logger
logger = logging.getLogger(__name__)

async def get_list_users_from_redis(role: str) -> list[dict[str, Any]] | None:
    """
    Get users from redis.
    """
    logger.info("Start: fetch users list from redis")
    try:
        list_users = await r.get(f"list_users:{role}")

        if not list_users:
            logger.info("Redis: users list wasn't found")
            return None

        data: list[dict[str, Any]] = json.loads(list_users)

        logger.info("Success: users list was fetched from redis")

        return data
    except Exception as e:
        logger.warning(f"Redis error: {e}")
        return None


async def save_list_users_to_redis(users: list[dict[str, Any]], role: str ) -> None:
    """
    Save users to redis.
    """
    logger.info("Start: saving users list to redis")

    try:
        ttl = timedelta(seconds=3600)
        await r.setex(f"list_users:{role}", int(ttl.total_seconds()), json.dumps(users))
        logger.info("Success: users list was saved to redis")
    except Exception as e:
        logger.warning(f"Redis error: {e}")
        pass
