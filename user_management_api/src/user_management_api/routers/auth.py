"""
Authentication module providing routers for user authentication,
including sign-up, login, logout and token refresh operations.
"""

from fastapi import APIRouter, Depends, Response, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.db.session import get_session
from src.user_management_api.schemas.auth import UserRegister, UserLogin
from src.user_management_api.services.auth import register_user, login_user, logout_user, renew_tokens
from src.user_management_api.utils.auth import get_access_token_from_cookie

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
) -> dict:
    """
    Log in a user.

    Args:
        response (Response): save JWT tokens in cookies.
        user_data (UserRegister): Data required to log in a user.
        db (AsyncSession): Database session.
    Returns:
        dict: Message about success of log in.
    """
    return await login_user(response, user_data, db)


@auth_router.post("/logout")
def logout_user_item(
        response: Response,
        token: str = Depends(get_access_token_from_cookie)
) -> dict:
    """
    Log out a user.

    Args:
        response (Response): save JWT tokens in cookies.
       token: access token from cookie.
    Returns:
        dict: Message about success of log out.
    """
    return logout_user(response, token)

@auth_router.post("/refresh-token")
def renew_tokens_item(
        request: Request,
        response: Response
) -> tuple:
    """
        Renew a couple JWT tokens with old refresh token.

        Args:
            response (Response): save JWT tokens in cookies.
            request: access token from cookie.
        Returns:
            tuple: access and refresh tokens.
        """
    return renew_tokens(request, response)