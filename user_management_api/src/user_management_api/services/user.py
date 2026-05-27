"""
The module providing handlers for the user information in a profile,
including  operations.
"""
import logging
import math
from operator import and_
from typing import Any, Sequence
from uuid import UUID

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.core.config import settings
from src.user_management_api.storage_s3.s3_client import  delete_file, create_presigned_url, \
    create_presigned_post, generate_image_s3_path
from src.user_management_api.dao.user import UserDAO
from src.user_management_api.db.session import get_session
from src.user_management_api.exceptions.auth import AuthenticationException
from src.user_management_api.exceptions.user import AuthorizationError, ResourceNotFound, S3StorageError
from src.user_management_api.models import User
from src.user_management_api.redis.redis_s3 import delete_presigned_url_from_redis, get_presigned_url_from_redis, \
    save_presigned_url_to_redis
from src.user_management_api.schemas.auth import CurrentUser
from src.user_management_api.schemas.user import ProfileUserPatch, PresignUrlGet, \
    PresignedPostResponse, ConfirmAvatarRequest, UserResponse, UserPatchByAdmin, UserFilter, UserPagination, \
    RoleResponse, GroupResponse
from src.user_management_api.services.auth import delete_refresh_token_from_redis, verify_refresh_token, \
    get_current_user
from src.user_management_api.utils.auth import delete_tokens_from_cookies

# Create a module specific logger
logger = logging.getLogger(__name__)


def serialize_user_data(user: User | None) -> UserResponse:
    if user is None:
        raise ResourceNotFound("User is not found")

    roles = [RoleResponse(id=role.id, role_name=role.role_name.value) for role in user.roles]
    group = GroupResponse(id=user.group.id, group_name=user.group.name) if user.group else None
    user_serialized = UserResponse(
        id=user.id,
        name=user.name,
        surname=user.surname,
        username=user.username,
        phone_number=user.phone_number,
        email=user.email,
        image_s3_path=user.image_s3_path,
        is_blocked=user.is_blocked,
        created_at=user.created_at,
        modified_at=user.modified_at,
        group=group,
        roles=roles
    )
    return user_serialized


async def get_me(
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user)
) -> UserResponse:
    """
    Return an information for authenticated user in a profile.

    Args:
        db (Session): Database session.
        current_user (CurrentUser): A user data from JWT access token for getting a user profile.
    Returns:
        UserResponse: The profile information for an authenticated user.
    """
    logger.info(f"Start: fetch user data by ID={current_user.user_id}")

    # Get user by ID.
    user = await UserDAO.find_one_or_none_with_related_data(db, User.id == current_user.user_id)

    logger.info("Success: getting serialized user data.")

    return serialize_user_data(user)


async def delete_me(
        request: Request,
        response: Response,
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user),
        bucket: str = settings.bucket_name,
) -> dict[str, str]:
    """
    Return an information about deletion of a user.

    Args:
        request (Request): Get an access token from cookies.
        response (Response):  Delete JWT tokens from cookie.
        db (Session): Database session.
        current_user (CurrentUser) : A user data from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
    Returns:
        dict: The message about deletion of a user.
    """
    logger.info(f"Start: deleting user token and data by ID={current_user.user_id}")

    #Verify refresh token to delete from redis.
    user_id_refresh, jti = await verify_refresh_token(request)

    if current_user.user_id == user_id_refresh:
        #Delete JWT tokens for the user.
        await delete_refresh_token_from_redis(user_id_refresh, jti)
        delete_tokens_from_cookies(response)

        #Delete an image from aws s3 and the way to the image from redis if exists
        user = await UserDAO.find_one_or_none(db, User.id == current_user.user_id)

        if user is None:
            raise ResourceNotFound("User is not found")

        if user.image_s3_path:
            await delete_file(bucket, user.image_s3_path)
            await delete_presigned_url_from_redis(current_user.user_id)

        await UserDAO.delete_by_id(db, current_user.user_id)
        await db.commit()

        logger.info("Success: deleting user data")

        return {"detail": "A user profile was deleted."}
    else:
        raise AuthenticationException


async def patch_me(
        data: ProfileUserPatch,
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user),
) -> UserResponse:
    """
    Return an updated user profile information.

    Args:
        db (AsyncSession): Database session.
        data (ProfileUserPatch): Incoming neu user data.
        current_user (CurrentUser): A user data from JWT access token for getting a user profile.
    Returns:
        UserResponse: Updated user profile information.
    """
    try:
        logger.info(f"Start: patch user data by ID={current_user.user_id}")
        await UserDAO.patch_by_id(db, current_user.user_id, data.model_dump(exclude_unset=True))
        await db.commit()
    except:
        await db.rollback()
        raise ResourceNotFound("User is not found")

    user = await UserDAO.find_one_or_none_with_related_data(db, User.id == current_user.user_id)

    logger.info("Success: getting patched serialized user data")
    return serialize_user_data(user)


async def get_avatar(
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user),
        bucket: str = settings.bucket_name,
        region_name: str = settings.aws_region,
) -> PresignUrlGet:
    """
    Return a presign url for an avatar usage.

    Args:
        db (AsyncSession): Database session.
        current_user (CurrentUser) : A user data from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
        region_name
    Returns:
        PresignUrlGet: Presign url from redis to an avatar usage.
    """
    logger.info("Start: fetch user avatar")

    presigned_url = await get_presigned_url_from_redis(current_user.user_id)
    if not presigned_url:
        user = await UserDAO.find_one_or_none(db, User.id == current_user.user_id)

        if user is None:
            raise ResourceNotFound("User is not found")

        if user.image_s3_path is None:
            raise S3StorageError("A way to the avatar in the database is not exist.")

        presigned_url = await create_presigned_url(bucket, user.image_s3_path, region_name, expiration=3600)
        await save_presigned_url_to_redis(presigned_url, current_user.user_id)

    logger.info("Success: getting user avatar")

    return PresignUrlGet(presigned_url=presigned_url)


async def get_presigned_post(
        current_user: CurrentUser = Depends(get_current_user),
        bucket: str = settings.bucket_name,
        region_name: str = settings.aws_region,
) -> PresignedPostResponse:
    """
    Update a user avatar.

    Args:
        current_user (CurrentUser): A user ID from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
        region_name: AWS region where the s3 bucket is located.
    Returns:
        PresignedPostResponse: Data required to upload the file to s3 directly.
    """
    logger.info("Start: sending user avatar to s3.")

    new_image_s3_path = generate_image_s3_path(current_user.user_id)
    post = await create_presigned_post(bucket, new_image_s3_path, region_name, expiration=3600)

    post_response =  PresignedPostResponse(
        key=new_image_s3_path,
        url=post["url"],
        fields=post["fields"]
    )

    logger.info("Success: user avatar was sent to s3")

    return post_response


async def confirm_avatar(
        body: ConfirmAvatarRequest,
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user),
        bucket: str = settings.bucket_name,
        region_name: str = settings.aws_region,
) -> UserResponse:
    """
    Return a presign url for an avatar usage.

    Args:
        body (ConfirmAvatarRequest): Contains key, a path to a new avatar user.
        db (AsyncSession): Database session.
        current_user (CurrentUser): A user data from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
        region_name: AWS region where the s3 bucket is located.
    Returns:
         UserResponse: Partially updated user profile information.
    """
    logger.info("Start: confirm saving user avatar path into the DB")

    new_image_s3_path = body.key

    user = await UserDAO.find_one_or_none(db, User.id == current_user.user_id)

    if user is None:
        raise ResourceNotFound("User is not found")

    try:
        await UserDAO.patch_by_id(db, current_user.user_id, {"image_s3_path": new_image_s3_path})
        await db.commit()
    except:
        await db.rollback()
        raise ResourceNotFound("User is not found")

    if user.image_s3_path:
        await delete_file(bucket, user.image_s3_path)
        await delete_presigned_url_from_redis(current_user.user_id)

    presigned_url = await create_presigned_url(bucket, new_image_s3_path, region_name, expiration=3600)
    await save_presigned_url_to_redis(presigned_url, current_user.user_id)

    user = await UserDAO.find_one_or_none_with_related_data(db, User.id == current_user.user_id)

    logger.info("Success: user avatar path is saved into the DB")

    return serialize_user_data(user)


async def delete_avatar(
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user),
        bucket: str = settings.bucket_name,
) -> UserResponse:
    """
    Return a presign url for an avatar usage.

    Args:
        db (AsyncSession): Database session.
        current_user (CurrentUser): A user data from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
    Returns:
         UserResponse: Partially updated user profile information.
    """
    logger.info("Start: deleting user avatar from s3")

    user = await UserDAO.find_one_or_none(db, User.id == current_user.user_id)

    if user is None:
        raise ResourceNotFound("User is not found")

    if user.image_s3_path:
        try:
            await UserDAO.patch_by_id(db, current_user.user_id, {"image_s3_path": None})
            await db.commit()
        except:
            await db.rollback()
            raise ResourceNotFound("User is not found")
        await delete_file(bucket, user.image_s3_path)
        await delete_presigned_url_from_redis(current_user.user_id)

    user = await UserDAO.find_one_or_none_with_related_data(db, User.id == current_user.user_id)

    logger.info("Success: user avatar was deleted")

    return serialize_user_data(user)


async def get_user(
        user_id: UUID,
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user)
) -> UserResponse | None:
    """
    Get information about a user profile by ID.

    Args:
        user_id: ID user for getting information about this user.
        db (AsyncSession): Database session.
        current_user (CurrentUser): A user (admin, moderator) ID from JWT access token who requests information.
    Returns:
        UserResponse: An information about a user profile by ID.
    """
    logger.info(f"Start: fetch user data by ID={user_id} for ADMIN/MODERATOR role.")

    if "ADMIN" in current_user.roles:
        user = await UserDAO.find_one_or_none_with_related_data(db, User.id == user_id)
        if not user:
            raise ResourceNotFound("User is not found")

    elif "MODERATOR" in current_user.roles:
        user = await UserDAO.find_one_or_none_with_related_data(db, and_(User.id == user_id, User.group_id == current_user.group_id))
        if not user:
            raise AuthorizationError("Not allowed")
    else:
        raise AuthorizationError("Not allowed")

    logger.info("Success: getting serialized user data")

    return serialize_user_data(user)


async def patch_user(
        user_id: UUID,
        data: UserPatchByAdmin,
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user)
) -> UserResponse:
    """
    Get information about a user profile by ID.

    Args:
        user_id: ID user for getting information about this user.
        data (UserPatchByAdmin):  Incoming new user data.
        db (AsyncSession): Database session.
        current_user (CurrentUser): A user (admin, moderator) ID from JWT access token who requests information.
    Returns:
        UserResponse: Updated user profile information.
    """
    logger.info(f"Start: patch user data by ID={user_id} for ADMIN.")

    if "ADMIN" in current_user.roles:
        data_user = data.model_dump(exclude_unset=True)
        roles_id = data_user.pop("roles_id", None)
        try:
            await UserDAO.patch_by_id(db, user_id, data_user)
            if roles_id is not None:
                await UserDAO.update_user_role(db, user_id, roles_id)
            await db.commit()
        except:
            await db.rollback()
            raise ResourceNotFound("User is not found")
        user = await UserDAO.find_one_or_none_with_related_data(db, User.id == user_id)
    else:
        raise AuthorizationError("Not allowed")

    logger.info("Success: getting patched serialized user data for ADMIN")

    return serialize_user_data(user)


async def get_response_list(list_users: Sequence[User]) -> list[UserResponse]:
    """
    Create serialized list users for a role (admin, moderator).
    """
    new_list: list[UserResponse] = []
    for user in list_users:
        user_serialized = serialize_user_data(user)
        new_list.append(user_serialized)
    return new_list


async def get_users(
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user),
        user_filter: UserFilter = Depends(),
        pagination: UserPagination = Depends()
) -> dict[str, Any]:
    """
    Get information about a user profile by ID.

    Args:
        db (AsyncSession): Database session.
        current_user (CurrentUser): A user (admin, moderator) ID from JWT access token who requests information.
        user_filter (UserFilter): A schema for filter and sorting information for loading.
        pagination (UserPagination): Pagination for list of users.
    Returns:
        dict : Data for each role of current user.
    """
    logger.info(f"Start: fetch users list for ADMIN/MODERATOR role.")

    response = {}
    roles = {
        "ADMIN": None,
        "MODERATOR": User.group_id == current_user.group_id
    }

    for role, role_condition in roles.items():
        # Check allowed role.
        if not role in current_user.roles:
            continue

        # Get data from database.
        users, total_users = await UserDAO.get_all(db, pagination, role_condition, user_filter)

        # Get serialized list of users with pagination data
        list_users = await get_response_list(users)
        response[f'{role}'] = {
            "users": list_users,
            "total_users": total_users,
            "page": pagination.page,
            "size": pagination.size,
            "total_pages": math.ceil(total_users/pagination.size)
        }

    # Raise error for roles except admin and moderator.
    if response == {}:
        raise AuthorizationError("Not allowed")

    logger.info(f"Success: getting serialized users list data.")

    return response