"""
User module providing routers for user information,
including get, patch and delete operations.
"""
from typing import Any

from fastapi import APIRouter, Depends, Request, Response, BackgroundTasks
from fastapi_filter import FilterDepends
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import APIKeyCookie

from src.user_management_api.core.config import settings
from src.user_management_api.db.session import get_session
from src.user_management_api.schemas.auth import CurrentUser
from src.user_management_api.schemas.user import ProfileUserPatch, PresignUrlGet, UserPagination, \
    PresignedPostResponse, ConfirmAvatarRequest, UserResponse, UserPatchByAdmin, UserFilter
from src.user_management_api.services.auth import get_current_user
from src.user_management_api.services.user import get_me, delete_me, patch_me, get_avatar, \
    delete_avatar, get_presigned_post, confirm_avatar, get_user, patch_user, get_users

user_router = APIRouter(prefix="/user", tags=["User"])
users_router = APIRouter(prefix="/users", tags=["Users"])

cookie_schema = APIKeyCookie(name="access_token")


@user_router.get("/me", response_model=UserResponse, dependencies=[Depends(cookie_schema)])
async def get_me_item(
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user)
) -> UserResponse:
    """
    Information for authenticated user in a profile.

    Args:
        db (AsyncSession): Database session.
        current_user (CurrentUser): A user ID from JWT access token for getting a user profile.
    Returns:
        UserResponse: The profile information for an authenticated user.
    """
    return await get_me(db, current_user)


@user_router.delete("/me", dependencies=[Depends(cookie_schema)])
async def delete_me_item(
        request: Request,
        response: Response,
        background_tasks: BackgroundTasks,
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user),
        bucket: str = settings.bucket_name,
)-> dict[str, str]:
    """
    Delete a user profile.

    Args:
        request (Request): Get an access token from cookies.
        response (Response):  Delete JWT tokens from cookie.
        background_tasks (BackgroundTasks): Schedules publishing the message asynchronously.
        db (AsyncSession): Database session.
        current_user (CurrentUser) : A user ID from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
    Returns:
        dict: The message about deletion of a user.
    """
    return await delete_me(request, response, background_tasks, db, current_user, bucket)


@user_router.patch("/me", response_model=UserResponse, dependencies=[Depends(cookie_schema)])
async def patch_me_item(
        data: ProfileUserPatch,
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user),
) -> UserResponse:
    """
    Update a user profile partially.

    Args:
        db (AsyncSession): Database session.
        data (ProfileUserPatch): Incoming new user data.
        current_user (CurrentUser): A user ID from JWT access token for getting a user profile.
    Returns:
        UserResponse: Updated user profile information.
    """
    return await patch_me(data, db, current_user)


@user_router.get("/me/avatar", response_model=PresignUrlGet, dependencies=[Depends(cookie_schema)])
async def get_avatar_item(
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user),
        bucket: str = settings.bucket_name,
        region_name: str = settings.aws_region,
) -> PresignUrlGet:
    """
    Get a user avatar for other pages  using url from redis.

    Args:
        db (AsyncSession): Database session.
        current_user (CurrentUser) : A user ID from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
        region_name
    Returns:
        PresignUrlGet: Presign url from redis to an avatar usage.
    """
    return await get_avatar(db, current_user, bucket, region_name)


@user_router.post("/me/avatar/presigned-post", response_model=PresignedPostResponse, dependencies=[Depends(cookie_schema)])
async def get_presigned_post_avatar(
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
    return await get_presigned_post(current_user, bucket, region_name)


@user_router.patch("/me/avatar/confirm", response_model=UserResponse, dependencies=[Depends(cookie_schema)])
async def patch_confirm_avatar(
        body: ConfirmAvatarRequest,
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user),
        bucket: str = settings.bucket_name,
        region_name: str = settings.aws_region,
) -> UserResponse:
    """
    Confirm avatar upload.

    Args:
        body (ConfirmAvatarRequest): Contains key, a path to a new avatar user.
        db (AsyncSession): Database session.
        current_user (CurrentUser): A user ID from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
        region_name: AWS region where the s3 bucket is located.
    Returns:
         UserResponse: Updated user profile information
    """
    return await confirm_avatar(body, db, current_user, bucket, region_name)


@user_router.delete("/me/avatar", response_model=UserResponse, dependencies=[Depends(cookie_schema)])
async def delete_avatar_item(
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user),
        bucket: str = settings.bucket_name,
) -> UserResponse:
    """
    Delete a user avatar.

    Args:
        db (AsyncSession): Database session.
        current_user (CurrentUser): A user ID from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
    Returns:
         UserResponse: Updated user profile information
    """
    return await delete_avatar(db, current_user, bucket)


@user_router.get("/{user_id}", response_model=UserResponse, dependencies=[Depends(cookie_schema)])
async def get_user_by_id(
        user_id: str,
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
    return await get_user(user_id, db, current_user)


@user_router.patch("/{user_id}", response_model=UserResponse, dependencies=[Depends(cookie_schema)])
async def patch_user_by_id(
        user_id: str,
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
    return await patch_user(user_id, data, db, current_user)


@users_router.get("/", dependencies=[Depends(cookie_schema)])
async def get_users_list(
        db: AsyncSession = Depends(get_session),
        current_user: CurrentUser = Depends(get_current_user),
        user_filter: UserFilter = FilterDepends(UserFilter),
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
    return await get_users(db, current_user,user_filter, pagination)