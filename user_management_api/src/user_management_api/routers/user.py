"""
User module providing routers for user information,
including get, patch and delete operations.
"""

from fastapi import APIRouter, Depends, Request, Response, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import APIKeyCookie

from src.user_management_api.core.config import settings
from src.user_management_api.db.session import get_session
from src.user_management_api.schemas.user import ProfileUserGet, ProfileUserPatch, ProfileUserResponse, \
    PresignUrlGet
from src.user_management_api.services.auth import get_current_user
from src.user_management_api.services.user import get_me, delete_me, patch_me, get_avatar, patch_avatar, \
    delete_avatar

user_router = APIRouter(prefix="/user")

cookie_schema = APIKeyCookie(name="access_token")

@user_router.get("/me", response_model=ProfileUserGet, dependencies=[Depends(cookie_schema), Depends(get_current_user)])
async def get_me_item(
        db: AsyncSession = Depends(get_session),
        user_id: str = Depends(get_current_user)
) -> ProfileUserGet:
    """
    Information for authenticated user in a profile.

    Args:
        db (AsyncSession): Database session.
        user_id: A user ID from JWT access token for getting a user profile.
    Returns:
        ProfileUserGet: The profile information for an authenticated user.
    """
    return await get_me(db, user_id)


@user_router.delete("/me", dependencies=[Depends(cookie_schema), Depends(get_current_user)])
async def delete_me_item(
        request: Request,
        response: Response,
        db: AsyncSession = Depends(get_session),
        user_id_access: str = Depends(get_current_user),
        bucket: str = settings.bucket_name,
)-> dict[str, str]:
    """
    Delete a user profile.

    Args:
        request (Request): Get an access token from cookies.
        response (Response):  Delete JWT tokens from cookie.
        db (AsyncSession): Database session.
        user_id_access: A user ID from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
    Returns:
        dict: The message about deletion of a user.
    """
    return await delete_me(request, response, db, user_id_access, bucket)


@user_router.patch("/me", response_model=ProfileUserResponse, dependencies=[Depends(cookie_schema), Depends(get_current_user)])
async def patch_me_item(
        data: ProfileUserPatch,
        db: AsyncSession = Depends(get_session),
        user_id: str = Depends(get_current_user),
) -> ProfileUserResponse:
    """
    Update a user profile partially.

    Args:
        db (AsyncSession): Database session.
        data (ProfileUserPatch): Incoming neu user data.
        user_id: A user ID from JWT access token for getting a user profile.
    Returns:
        ProfileUserResponse: Partially updated user profile information.
    """
    return await patch_me(data, db, user_id)


@user_router.get("/me/avatar", dependencies=[Depends(cookie_schema), Depends(get_current_user)])
async def get_avatar_item(
        db: AsyncSession = Depends(get_session),
        user_id: str = Depends(get_current_user),
        bucket: str = settings.bucket_name,
        region_name: str = settings.aws_region,
) -> PresignUrlGet:
    """
    Get a user avatar for other pages  using url from redis.

    Args:
        db (AsyncSession): Database session.
        user_id: A user ID from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
        region_name
    Returns:
        PresignUrlGet: Presign url from redis to an avatar usage.
    """
    return await get_avatar(db, user_id, bucket, region_name)


@user_router.patch("/me/avatar", dependencies=[Depends(cookie_schema), Depends(get_current_user)])
async def patch_avatar_item(
        file: UploadFile = File(...),
        db: AsyncSession = Depends(get_session),
        user_id: str = Depends(get_current_user),
        bucket: str = settings.bucket_name,
        region_name: str = settings.aws_region,
) -> ProfileUserResponse:
    """
    Update a user avatar.

    Args:
        file
        db (AsyncSession): Database session.
        user_id: A user ID from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
        region_name
    Returns:
         ProfileUserResponse: Partially updated user profile information
    """
    return await patch_avatar(file, db, user_id, bucket, region_name)


@user_router.delete("/me/avatar", dependencies=[Depends(cookie_schema), Depends(get_current_user)])
async def delete_avatar_item(
        db: AsyncSession = Depends(get_session),
        user_id: str = Depends(get_current_user),
        bucket: str = settings.bucket_name,
) -> ProfileUserResponse:
    """
    Delete a user avatar.

    Args:
        db (AsyncSession): Database session.
        user_id: A user ID from JWT access token for getting a user profile.
        bucket: The bucket name in AWS S3.
    Returns:
         ProfileUserResponse: Partially updated user profile information
    """
    return await delete_avatar(db, user_id, bucket)
