"""
This module is designed to work with a s3_client.

Defines functions for upload a file, delete a file,
replace a file, cache a file.
"""

from datetime import timedelta

from botocore.exceptions import ClientError
from fastapi import UploadFile

from src.user_management_api.core.config import s3, r
from src.user_management_api.exceptions.user import S3StorageError, FileValidateError

def validate_file_uploaded(file) -> None:
    """
    Validate an avatar image from a user.
    """
    if not file.content_type.startswith("image/"):
        raise FileValidateError(detail="Only images are allowed.")

    ext = file.filename.split(".")[-1].lower()
    if ext not in ["jpg", "jpeg", "png", "webp"]:
        raise FileValidateError(detail="Invalid file format.")

    file.file.seek(0,2)
    size_file = file.file.tell()
    file.file.seek(0)

    if size_file > 2*1024*1024:
        raise FileValidateError(detail="The file is too large.")

def generate_image_s3_path(file: UploadFile, user_id) -> str:
    """
    Create image_s3_path for a user avatar.
    """
    ext = file.filename.split(".")[-1].lower()
    file_name = file.filename.split(".")[0].lower()
    image_s3_path = f"users/avatar/{user_id}_{file_name}.{ext}"
    return image_s3_path


def upload_file(file: UploadFile, bucket, image_s3_path) -> None:
    """
    Upload a file to an S3 bucket.
    """
    try:
        s3.upload_fileobj(file.file, bucket, image_s3_path)
    except ClientError:
        raise S3StorageError("The file is not uploaded")


def delete_file(bucket, image_s3_path) -> None:
    """
    Delete a file from an S3 bucket.
    """
    try:
        s3.delete_object(Bucket=bucket, Key=image_s3_path)
    except ClientError:
        raise S3StorageError("The file is not deleted")


def create_presigned_url(bucket, image_s3_path, region_name, expiration=3600) -> str | None:
    """
    Generate a presigned URL to share an S3 object.
    """
    if not image_s3_path:
        raise S3StorageError("A way to the avatar in the database is not exist.")
    try:
        presigned_url = s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": image_s3_path},
            ExpiresIn=expiration,
        )
        return presigned_url
    except ClientError:
        raise S3StorageError("The presignedurl is not created")


async def save_presigned_url_to_redis(presigned_url, user_id) -> None:
    """
    Save predesign_url to redis.
    """
    ttl = timedelta(days=30)
    await r.setex(f"presigned_url:{user_id}", int(ttl.total_seconds()), presigned_url)


async def delete_presigned_url_from_redis(user_id) -> None:
    """
    Delete predesign_url from redis.
    """
    try:
        await r.delete(f"presigned_url:{user_id}")
    except:
        pass


async def get_presigned_url_from_redis(user_id) ->str | None:
    """
    Get predesign_url from redis.
    """
    try:
        return await r.get(f"presigned_url:{user_id}")
    except:
        return None


async def replace_file(bucket, user_id, old_image_s3_path, file: UploadFile, region_name) -> str:
    """
    Replace an old image by a new one in s3 and change a way to the S3 image in the database.
    """
    try:
        validate_file_uploaded(file)

        new_image_s3_path = generate_image_s3_path(file, user_id)

        # Create a path for a new file in the database.
        upload_file(file, bucket, new_image_s3_path)

        # Delete a file from bucket.
        if old_image_s3_path:
            delete_file(bucket, old_image_s3_path)

        # Delete predesign url for a user in redis.
        await delete_presigned_url_from_redis(user_id)

        #Set presigned url of an image if it exists
        presigned_url = create_presigned_url(bucket, new_image_s3_path, region_name, expiration=3600)
        if presigned_url:
            await save_presigned_url_to_redis(presigned_url, user_id)

        return new_image_s3_path

    except S3StorageError:
        raise