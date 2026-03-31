"""
The module providing handlers for the user information in a profile,
including  operations.
"""

from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.dao.group import GroupDAO
from src.user_management_api.dao.user import UserDAO
from src.user_management_api.db.session import get_session
from src.user_management_api.models import User, Group
from src.user_management_api.schemas.user import ProfileUserGet, ProfileUserPatch, ProfileUserResponse
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
    user = await UserDAO.find_one_or_none(db, User.id == user_id)

    if user.group_id:
        group = await GroupDAO.find_one_or_none(db, Group.id == user.group_id)
        group_name = group.name
    else: group_name = ""

    return ProfileUserGet(
        name=str(user.name),
        surname=str(user.surname),
        username=str(user.username),
        phone_number=user.phone_number,
        email=str(user.email),
        image_s3_path=str(user.image_s3_path),
        group_name=group_name
    )


async def delete_me(
        request: Request,
        response: Response,
        db: AsyncSession = Depends(get_session),
        user_id_access: str = Depends(get_current_user)
) -> dict[str, str]:
    """
    Return an information about deletion of a user.

    Args:
        request (Request): Get an access token from cookies.
        response (Response):  Delete JWT tokens from cookie.
        db (Session): Database session.
        user_id_access: A user ID from JWT access token for getting a user profile.
    Returns:
        dict: The message about deletion of a user.
    """
    user_id_refresh, jti = await verify_refresh_token(request)

    if user_id_access == user_id_refresh:
        await delete_refresh_token_from_redis(user_id_refresh, jti)
        delete_tokens_from_cookies(response)
        await UserDAO.delete_by_id(db, user_id_access)
        await db.commit()

    return {"detail": "A user profile was deleted."}


async def patch_me(
        data: ProfileUserPatch,
        db: AsyncSession = Depends(get_session),
        user_id: str = Depends(get_current_user)
) -> ProfileUserResponse:
    """
    Return a partially updated user profile information.

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
