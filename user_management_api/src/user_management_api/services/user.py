"""
The module providing handlers for the user information in a profile,
including  operations.
"""

from fastapi import Depends, Request
from mypyc.build import group_name
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.core.security import decode_token, validate_access_token
from src.user_management_api.dao.group import GroupDAO
from src.user_management_api.dao.user import UserDAO
from src.user_management_api.db.session import get_session
from src.user_management_api.models import User, Group
from src.user_management_api.schemas.user import UserResponse
from src.user_management_api.utils.auth import get_access_token_from_cookie

async def get_me(request: Request, db: AsyncSession = Depends(get_session)) -> UserResponse:
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
        group = await GroupDAO.find_one_or_none(db, user.group_id == Group.id)
    return UserResponse(
        name=user.name,
        surname=user.surname,
        username=user.username,
        phone_number=user.phone_number,
        email=user.email,
        image=user.image_s3_path,
        group_name=group.name
    )