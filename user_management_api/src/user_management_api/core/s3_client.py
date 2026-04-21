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

from src.user_management_api.core.config import r, settings
from src.user_management_api.exceptions.user import S3StorageError


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
    try:
        async with s3_session.client("s3") as s3:
            await s3.delete_object(Bucket=bucket, Key=image_s3_path)
    except ClientError as e:
        logging.error(e)
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
            return post
    except ClientError as e:
        logging.error(e)
        raise S3StorageError("The presigned post is not generated")

async def create_presigned_url(
        bucket: str,
        image_s3_path: str,
        region_name: str,
        expiration: int=3600) -> str:
    """
    Generate a presigned URL to share an S3 object.
    """
    if not image_s3_path:
        raise S3StorageError("A way to the avatar in the database is not exist.")
    try:
        async with s3_session.client("s3", region_name=region_name) as s3:
            presigned_url: str = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": image_s3_path},
                ExpiresIn=expiration,
            )
            return presigned_url
    except ClientError as e:
        logging.error(e)
        raise S3StorageError("The presignedurl is not created")


async def save_presigned_url_to_redis(presigned_url: str, user_id: str) -> None:
    """
    Save predesign_url to redis.
    """
    ttl = timedelta(seconds=3600)
    await r.setex(f"presigned_url:{user_id}", int(ttl.total_seconds()), presigned_url)


async def delete_presigned_url_from_redis(user_id: str) -> None:
    """
    Delete predesign_url from redis.
    """
    try:
        await r.delete(f"presigned_url:{user_id}")
    except:
        pass


async def get_presigned_url_from_redis(user_id: str) ->str | None:
    """
    Get predesign_url from redis.
    """
    try:
        presigned_url: str | None = await r.get(f"presigned_url:{user_id}")
        return presigned_url
    except:
        return None