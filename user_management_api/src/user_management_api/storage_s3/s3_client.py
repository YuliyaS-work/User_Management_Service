"""
This module is designed to work with a s3_client.

Defines functions for upload a file, delete a file,
replace a file, cache a file.
"""
import logging
import time
from typing import Any

from botocore.exceptions import ClientError

from src.user_management_api.exceptions.user import S3StorageError
from src.user_management_api.storage_s3.s3_config import s3_session

# Create a module specific logger
logger = logging.getLogger(__name__)


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

    except ClientError:
        logger.exception(
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
    logger.info(f"Start: generating presigned post to avatar upload, bucket={bucket}, key={image_s3_path}")

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

            logger.info(f"Success: presigned post to avatar upload was generated, bucket={bucket}, key={image_s3_path}")

            return post
    except ClientError:
        logger.exception(
            "S3 rejected the request",
            extra={"bucket": bucket, "key": image_s3_path}
        )
        raise S3StorageError("Presigned post is not generated")

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
    except ClientError:
        logger.exception(
            "S3 rejected the request",
            extra={"bucket": bucket, "key": image_s3_path}
        )
        raise S3StorageError("The presigned url is not created")