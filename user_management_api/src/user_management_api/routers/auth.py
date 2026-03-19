"""
Authentication module providing routers for user authentication,
including sign-up, login, logout and token refresh operations.
"""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.db.session import get_session
from src.user_management_api.schemas.auth import UserRegister
from src.user_management_api.services.auth import register_user



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