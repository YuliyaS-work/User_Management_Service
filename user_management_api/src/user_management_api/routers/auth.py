"""
Authentication module providing routers for user authentication,
including sign-up, login, logout and token refresh operations.
"""
from fastapi import APIRouter, Depends, Response, Request, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.db.session import get_session
from src.user_management_api.schemas.auth import UserRegister, UserLogin, TokenResponse, ResetPasswordRequest, \
    ForgetPasswordRequest
from src.user_management_api.services.auth import register_user, login_user, logout_user, renew_tokens, reset_password, \
    save_password

auth_router = APIRouter(prefix="/test_core", tags=["Auth"])


@auth_router.post("/signup", response_model=TokenResponse, status_code=201)
async def register_user_item(
        response: Response,
        user_data: UserRegister,
        db: AsyncSession = Depends(get_session)
) -> TokenResponse:
    """
    Register a user.

    Args:
        response (Response): save JWT tokens in cookies.
        user_data (UserRegister): Data required to create a new user.
        db (AsyncSession): Database session.
    Returns:
        TokenResponse: An access and refresh tokens.
    """
    return await register_user(response, user_data, db)


@auth_router.post("/login", response_model=TokenResponse)
async def login_user_item(
        request: Request,
        response: Response,
        user_data: UserLogin,
        db: AsyncSession = Depends(get_session)
) -> TokenResponse:
    """
    Log in a user.

    Args:
        response (Response): save JWT tokens in cookies.
        user_data (UserRegister): Data required to log in a user.
        db (AsyncSession): Database session.
    Returns:
        TokenResponse: an access and refresh tokens.
    """
    return await login_user(request, response, user_data, db)


@auth_router.post("/logout", response_model=None, status_code=201)
async def logout_user_item(
        response: Response,
        request: Request
) -> dict[str, str]:
    """
    Log out a user.

    Args:
        response (Response): save JWT tokens in cookies.
        request (Request): get JWT tokens from cookies.
    Returns:
        dict: Message about success of log out.
    """
    return await logout_user(response, request)


@auth_router.post("/refresh-token", response_model=TokenResponse)
async def renew_tokens_item( request: Request, response: Response, db: AsyncSession = Depends(get_session)) -> TokenResponse:
    """
    Renew a couple JWT tokens with old refresh token.

    Args:
        response (Response): save JWT tokens in cookies.
        request: access token from cookies.
        db (AsyncSession): Database session.
    Returns:
        TokenResponse: access and refresh tokens.
    """
    return await renew_tokens(request, response, db)


@auth_router.post("/reset-password")
async def reset_password_item(
        background_tasks: BackgroundTasks,
        data: ForgetPasswordRequest,
        request: Request
) -> dict[str, str]:
    """
    Send a reset-password email message to RabbitMQ.

    Args:
        background_tasks (BackgroundTasks): Schedules publishing the message asynchronously.
        data (ForgetPasswordRequest): A user's email used to generate reset token.
        request (Request): used to build the reset-password URL.

    Returns:
        dict[str, str]: Confirm that the message was published to RabbitMQ.
    """
    return await reset_password(background_tasks, data, request)


@auth_router.post("/save-password")
async def save_password_item(
        data: ResetPasswordRequest,
        db: AsyncSession = Depends(get_session)
) -> dict[str, str]:
    """
    Update the user's password using a valid reset-password token.

    Args:
        data (ResetPasswordRequest): A token and a new password provided by the user.
        db (AsyncSession): Database session.
    Returns:
        dict[str,str]: Confirm a message about the password update result.
    """
    return await save_password(data, db)