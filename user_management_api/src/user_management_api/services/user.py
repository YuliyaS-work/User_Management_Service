"""
The module providing handlers for the user information in a profile,
including  operations.
"""
import phonenumbers
from fastapi import Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.core.security import decode_token, validate_access_token
from src.user_management_api.dao.group import GroupDAO
from src.user_management_api.dao.user import UserDAO
from src.user_management_api.db.session import get_session
from src.user_management_api.models import User, Group
from src.user_management_api.schemas.user import ProfileUserResponse
from src.user_management_api.services.auth import delete_refresh_token_from_redis, verify_refresh_token_and_delete
from src.user_management_api.utils.auth import get_access_token_from_cookie, delete_tokens_from_cookies


async def get_me(request: Request, db: AsyncSession = Depends(get_session)) -> ProfileUserResponse:
    """
    Return an information for authenticated user in a profile.

    Args:
        request (Request): Get an access token from cookies.
        db (Session): Database session.
    Returns:
        UserResponse: The profile information for an authenticated user.
    """
    access_token = get_access_token_from_cookie(request)
    payload = decode_token(access_token)
    user_id = validate_access_token(payload)

    user = await UserDAO.find_one_or_none(db, User.id == user_id)

    if user.group_id:
        group = await GroupDAO.find_one_or_none(db, Group.id == user.group_id)
        group_name = group.name
    else: group_name = ""

    if user.phone_number:
        phone_number = phonenumbers.format_number(user.phone_number, phonenumbers.PhoneNumberFormat.E164)

    return ProfileUserResponse(
        name=user.name,
        surname=user.surname,
        username=user.username,
        phone_number=phone_number,
        email=user.email,
        image=user.image_s3_path,
        group_name=group_name
    )


async def delete_me(request: Request, response: Response, db: AsyncSession = Depends(get_session)) -> dict[str, str]:
    """
    Return an information about deletion of a user.

    Args:
        request (Request): Get an access token from cookies.
        db (Session): Database session.
    Returns:
        dict: The message about deletion of a user.
    """
    access_token = get_access_token_from_cookie(request)
    payload = decode_token(access_token)
    user_id_access = validate_access_token(payload)
    user_id_refresh, jti = await verify_refresh_token_and_delete(request)

    if user_id_access == user_id_refresh:
        await delete_refresh_token_from_redis(user_id_refresh, jti)
        delete_tokens_from_cookies(response)
        await UserDAO.delete_one_by_id(user_id_access, db,)
        await db.commit()



    return {"detail": "A user profile was deleted."}



