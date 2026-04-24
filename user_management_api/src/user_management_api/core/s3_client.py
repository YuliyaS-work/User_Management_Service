"""
This module is designed to work with a s3_client.

Defines functions for upload a file, delete a file,
replace a file, cache a file.
"""
import logging
import time
from datetime import timedelta
from typing import Any

from botocore.exceptions import ClientError
import aioboto3
from redis import RedisError

from src.user_management_api.core.config import r, settings
from src.user_management_api.exceptions.user import S3StorageError

logger = logging.getLogger(__name__)

s3_session = aioboto3.Session(
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region,
)

def generate_image_s3_path(user_id: str) -> str:
    """
    Create image_s3_path for a user avatar.
    """
    file_name = time.time_ns()
    image_s3_path = f"users/avatar/{user_id}_{file_name}.webp"
    return image_s3_path


async def delete_file(bucket: str, image_s3_path: str) -> None:
    """
    Delete a file from an S3 bucket.
    """
    logger.info(f"Start: deleting file from s3, bucket={bucket}, key={image_s3_path}")

    try:
        async with s3_session.client("s3") as s3:
            await s3.delete_object(Bucket=bucket, Key=image_s3_path)

        logger.info(f"Success: file from s3 was deleted, bucket={bucket}, key={image_s3_path}")

    except ClientError as e:
        logging.exception(
            "S3 rejected the request",
            extra={"bucket": bucket, "key": image_s3_path}
        )
        raise S3StorageError("The file is not deleted")


async def create_presigned_post(
        bucket: str,
        image_s3_path: str,
        region_name: str,
        expiration: int =3600
) -> dict[str, Any]:
    """
    Generate a presigned URL to share an S3 object.
    """
    logger.info(f"Start: saving user avatar to s3, bucket={bucket}, key={image_s3_path}")

    if not image_s3_path:
        raise S3StorageError("A path to the avatar in the database is not exist.")
    try:
        async with s3_session.client("s3", region_name=region_name) as s3:
            post: dict[str, Any] = await s3.generate_presigned_post(
                Bucket=bucket,
                Key=image_s3_path,
                Fields={'Content-Type': 'image/*'},
                Conditions=[
                    ['content-length-range', 0, 2097152],
                    ['starts-with', '$Content-Type', 'image/']
                ],
                ExpiresIn=expiration
            )

            logger.info(f"Success: user avatar was saved to s3, bucket={bucket}, key={image_s3_path}")

            return post
    except ClientError as e:
        logging.exception(
            "S3 rejected the request",
            extra={"bucket": bucket, "key": image_s3_path}
        )
        raise S3StorageError("The presigned post is not generated")

async def create_presigned_url(
        bucket: str,
        image_s3_path: str,
        region_name: str,
        expiration: int=3600) -> str:
    """
    Generate a presigned URL to share an S3 object.
    """
    logger.info(f"Start: creating presigned url avatar, bucket={bucket}, key={image_s3_path}")

    if not image_s3_path:
        raise S3StorageError("A way to the avatar in the database is not exist.")
    try:
        async with s3_session.client("s3", region_name=region_name) as s3:
            presigned_url: str = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": image_s3_path},
                ExpiresIn=expiration,
            )

            logger.info(f"Success: presigned url avatar was created, bucket={bucket}, key={image_s3_path}")

            return presigned_url
    except ClientError as e:
        logging.exception(
            "S3 rejected the request",
            extra={"bucket": bucket, "key": image_s3_path}
        )
        raise S3StorageError("The presignedurl is not created")


async def save_presigned_url_to_redis(presigned_url: str, user_id: str) -> None:
    """
    Save predesign_url to redis.
    """
    logger.info(f"Start: saving presigned url avatar to redis, url={presigned_url}, user ID={user_id}")
    try:
        ttl = timedelta(seconds=3600)
        await r.setex(f"presigned_url:{user_id}", int(ttl.total_seconds()), presigned_url)

        logger.info(f"Success: presigned url avatar was saved to redis, ulr={presigned_url}, user ID={user_id}")
    except RedisError as e:
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
    except RedisError as e:
        logger.warning(f"Redis error: {e}")
        pass


async def get_presigned_url_from_redis(user_id: str) ->str | None:
    """
    Get predesign_url from redis.
    """
    logger.info(f"Start: fetching presigned url avatar from redis by ID={user_id}")

    try:
        presigned_url: str | None = await r.get(f"presigned_url:{user_id}")

        logger.info(f"Success: available presigned url avatar was fetched from redis")
        return presigned_url
    except RedisError as e:
        logger.warning(f"Redis error: {e}")
        return None