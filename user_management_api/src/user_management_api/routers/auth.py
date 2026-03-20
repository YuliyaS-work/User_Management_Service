"""
Authentication module providing routers for user authentication,
including sign-up, login, logout and token refresh operations.
"""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.db.session import get_session
from src.user_management_api.models import User
from src.user_management_api.schemas.auth import UserRegister, UserLogin
from src.user_management_api.services.auth import register_user, login_user



auth_router = APIRouter(prefix="/auth")


@auth_router.post("/signup")
async def register_user_item(
        response: Response,
        user_data: UserRegister,
        db: AsyncSession = Depends(get_session)
) -> dict:
    """
    Register a user.

    Args:
        response (Response): save JWT tokens in cookies.
        user_data (UserRegister): Data required to create a new user.
        db (AsyncSession): Database session.
    Returns:
        dict: Message about success of registration.
    """
    return await register_user(response, user_data, db)


@auth_router.post("/login")
async def login_user_item(
        response: Response,
        user_data: UserLogin,
        db: AsyncSession = Depends(get_session)
) -> User | None:
    """
    Login a user.

    Args:
        user_data (UserRegister): Data required to login a user.
        db (AsyncSession): Database session.
    Returns:
        : .
    """
    return await login_user(response, user_data, db)