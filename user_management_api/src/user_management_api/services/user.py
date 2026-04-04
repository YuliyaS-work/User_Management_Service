"""
The module providing handlers for the user information in a profile,
including  operations.
"""
from typing import Any

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.core.config import settings
from src.user_management_api.core.s3_client import delete_presigned_url_from_redis, delete_file, \
    get_presigned_url_from_redis, save_presigned_url_to_redis, create_presigned_url, create_presigned_post, \
    generate_image_s3_path
from src.user_management_api.dao.user import UserDAO
from src.user_management_api.db.session import get_session
from src.user_management_api.exceptions.auth import AuthenticationException
from src.user_management_api.models import User
from src.user_management_api.schemas.user import ProfileUserGet, ProfileUserPatch, ProfileUserResponse, \
    PresignUrlGet, PresignedPostResponse, ConfirmAvatarRequest
from src.user_management_api.services.auth import delete_refresh_token_from_redis, verify_refresh_token, \
    get_current_user
from src.user_management_api.utils.auth import delete_tokens_from_cookies


async def get_me(
        db: AsyncSession = Depends(get_session),
        user_id: str = Depends(get_current_user)
) -> ProfileUserGet:
    """
    Return an information for authenticated user in a profile.

    Args:
        db (Session): Database session.
        user_id: A user ID from JWT access token for getting a user profile.
    Returns:
        ProfileUserGet: The profile information for an authenticated user.
    """
    # Get user by ID.
    user = await UserDAO.find_one_or_none(db, User.id == user_id)

    # Get group name for the user.
    if user.group_id:
        group_name = user.group.name
    else: group_name = ""

    return ProfileUserGet(
        name=str(user.name),
        surname=str(user.surname),
        username=str(user.username),
        phone_number=user.phone_number,
        email=str(user.email),
        group_name=group_name
    )


async def delete_me(
        request: Request,
        response: Response,
        db: AsyncSession = Depends(get_session),
        user_id_access: str = Depends(get_current_user),
        bucket: str = settings.bucket_name,
) -> dict[str, str]:
    """
    Return an information about deletion of a user.

    Args:
        request (Request): Get an access token from cookies.
        response (Response):  Delete JWT tokens from cookie.
        db (Session): Database session.
        user_id_access: A user ID from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
    Returns:
        dict: The message about deletion of a user.
    """
    #Verify refresh token to delete from redis.
    user_id_refresh, jti = await verify_refresh_token(request)

    if user_id_access == user_id_refresh:
        #Delete JWT tokens for the user.
        await delete_refresh_token_from_redis(user_id_refresh, jti)
        delete_tokens_from_cookies(response)

        #Delete an image from aws s3 and the way to the image from redis if exists
        user = await UserDAO.find_one_or_none(db, User.id == user_id_access)
        if user.image_s3_path:
            await delete_file(bucket, user.image_s3_path)
            await delete_presigned_url_from_redis(user_id_access)

        await UserDAO.delete_by_id(db, user_id_access)
        await db.commit()

        return {"detail": "A user profile was deleted."}
    else:
        raise AuthenticationException


async def patch_me(
        data: ProfileUserPatch,
        db: AsyncSession = Depends(get_session),
        user_id: str = Depends(get_current_user),
) -> ProfileUserResponse:
    """
    Return an updated user profile information.

    Args:
        db (AsyncSession): Database session.
        data (ProfileUserPatch): Incoming neu user data.
        user_id: A user ID from JWT access token for getting a user profile.
    Returns:
        ProfileUserResponse: Partially updated user profile information.
    """
    updated_user = await UserDAO.patch_by_id(db, user_id, data.model_dump(exclude_unset=True))

    await db.commit()

    return ProfileUserResponse.model_validate(updated_user)


async def get_avatar(
        db: AsyncSession = Depends(get_session),
        user_id: str = Depends(get_current_user),
        bucket: str = settings.bucket_name,
        region_name: str = settings.aws_region,
) -> PresignUrlGet:
    """
    Return a presign url for an avatar usage.

    Args:
        db (AsyncSession): Database session.
        user_id: A user ID from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
        region_name
    Returns:
        PresignUrlGet: Presign url from redis to an avatar usage.
    """
    presigned_url = await get_presigned_url_from_redis(user_id)
    if not presigned_url:
        user = await UserDAO.find_one_or_none(db, User.id == user_id)
        presigned_url = await create_presigned_url(bucket, user.image_s3_path, region_name, expiration=3600)
        await save_presigned_url_to_redis(presigned_url, user_id)
    return PresignUrlGet(presigned_url=presigned_url)


async def get_presigned_post(
        user_id: str = Depends(get_current_user),
        bucket: str = settings.bucket_name,
        region_name: str = settings.aws_region,
) -> PresignedPostResponse:
    """
    Update a user avatar.

    Args:
        user_id: A user ID from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
        region_name: AWS region where the s3 bucket is located.
    Returns:
        PresignedPostResponse: Data required to upload the file to s3 directly.
    """
    new_image_s3_path = generate_image_s3_path(user_id)
    post = await create_presigned_post(bucket, new_image_s3_path, region_name, expiration=3600)
    return PresignedPostResponse(
        key=new_image_s3_path,
        url=post["url"],
        fields=post["fields"]
    )


async def confirm_avatar(
        body: ConfirmAvatarRequest,
        db: AsyncSession = Depends(get_session),
        user_id: str = Depends(get_current_user),
        bucket: str = settings.bucket_name,
        region_name: str = settings.aws_region,

) -> ProfileUserResponse:
    """
    Return a presign url for an avatar usage.

    Args:
        body (ConfirmAvatarRequest): Contains key, a path to a new avatar user.
        db (AsyncSession): Database session.
        user_id: A user ID from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
        region_name: AWS region where the s3 bucket is located.
    Returns:
         ProfileUserResponse: Partially updated user profile information.
    """
    new_image_s3_path = body.key

    user = await UserDAO.find_one_or_none(db, User.id == user_id)

    if user.image_s3_path:
        await delete_file(bucket, user.image_s3_path)
        await delete_presigned_url_from_redis(user_id)

    updated_user = await UserDAO.patch_by_id(db, user_id, {"image_s3_path": new_image_s3_path})
    await db.commit()
    presigned_url = await create_presigned_url(bucket, new_image_s3_path, region_name, expiration=3600)
    await save_presigned_url_to_redis(presigned_url, user_id)

    return ProfileUserResponse.model_validate(updated_user)


async def delete_avatar(
        db: AsyncSession = Depends(get_session),
        user_id: str = Depends(get_current_user),
        bucket: str = settings.bucket_name,
) -> ProfileUserResponse:
    """
    Return a presign url for an avatar usage.

    Args:
        db (AsyncSession): Database session.
        user_id: A user ID from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
    Returns:
         ProfileUserResponse: Partially updated user profile information.
    """
    user = await UserDAO.find_one_or_none(db, User.id == user_id)
    if user.image_s3_path:
        await delete_file(bucket, user.image_s3_path)
        await delete_presigned_url_from_redis(user_id)
        user = await UserDAO.patch_by_id(db, user_id, {"image_s3_path": None})
        await db.commit()
    return ProfileUserResponse.model_validate(user)