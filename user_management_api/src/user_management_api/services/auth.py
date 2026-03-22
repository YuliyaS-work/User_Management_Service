"""Authentication module providing handlers for user authentication,
including sign-up, login, logout and token refresh operations.
"""

from fastapi import HTTPException, status, Response, Request, Depends

from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.core.security import get_password_hash, create_access_token, create_refresh_token, \
    verify_password, decode_token, validate_token
from src.user_management_api.models import User
from src.user_management_api.schemas.auth import UserRegister, UserLogin
from src.user_management_api.dao.user import UserDAO
from src.user_management_api.utils.auth import send_tokens_to_user, \
    get_access_token_from_cookie, delete_refresh_token_from_redis, delete_tokens_from_cookies, \
    get_refresh_token_from_cookie, save_refresh_token_to_redis


def create_and_store_tokens(user_id) -> tuple:
    access_token = create_access_token({"sub": user_id})
    refresh_token = create_refresh_token({"sub": user_id})
    save_refresh_token_to_redis(refresh_token, user_id)
    return access_token, refresh_token


async def register_user(response: Response, user_data: UserRegister, db: AsyncSession) -> dict:
    """
        Register a user and create a record in the database.

        Args:
            response (Response): save JWT tokens in cookies.
            user_data (UserRegister): Data required to create a new user in the database.
            db (AsyncSession): Database session.
        Returns:
            dict: Message about success of registration.
    """
    # Check that email and username are unique.
    user = await UserDAO.find_one_or_none(
        db,
        or_(User.username == user_data.username, User.email == user_data.email)
    )
    if user:
        if user.username == user_data.username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists"
            )
        if user.email == user_data.email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists"
            )
    # Get a dictionary of instance.
    user_dict = user_data.model_dump()

    # Get password hash.
    user_dict["password"] = get_password_hash(user_data.password)

    # Add a user to the database.
    new_user = await UserDAO.add(db, **user_dict)
    await db.commit()

    # UUID to string for JSON serialization to get tokens.
    user_id = str(new_user.id)

    access_token, refresh_token = create_and_store_tokens(user_id)
    send_tokens_to_user(response, access_token, refresh_token)

    return {"message": "User registered successfully"}


async def login_user(response: Response, user_data: UserLogin, db: AsyncSession) -> dict:
    """
        Check a user and login.

        Args:
            response (Response): save JWT tokens in cookies.
            user_data (UserRegister): Data required to create a new user in the database.
            db (AsyncSession): Database session.
        Returns:
            dict: Message about success of login.
    """
    user = await UserDAO.find_one_or_none(
        db,
        or_(
            User.username == user_data.username,
            User.email == user_data.email,
            User.phone_number == user_data.phone_number
        )
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User's not found."
        )

    # Get a password.
    password_db = user.password

    # Get provided password hash.
    plain_password = get_password_hash(user_data.password)

    verification = verify_password(plain_password, password_db)

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Password's not correct."
        )

    # UUID to string for JSON serialization to get tokens.
    user_id = str(user.id)

    access_token, refresh_token = create_and_store_tokens(user_id)
    send_tokens_to_user(response, access_token, refresh_token)

    return {"message": "User logged in"}


def logout_user(response: Response, token: str = Depends(get_access_token_from_cookie)) -> dict:
    """
    Log out a user.

    Args:
        response (Response): save JWT tokens in cookies.
        token: access token from cookie.
    Returns:
        dict: Message about success of log out.
    """
    payload = decode_token(token)

    if payload:
        user_id = payload.get('sub')
        jti = payload.get("jti")

        if user_id and jti:
            delete_refresh_token_from_redis(user_id, jti)

    delete_tokens_from_cookies(response)

    return {"message": "User logged out"}


def renew_tokens(request: Request, response: Response) -> tuple:
    refresh_token = get_refresh_token_from_cookie(request)
    payload = decode_token(refresh_token)
    user_id = validate_token(response, payload)
    access_token, refresh_token = create_and_store_tokens(user_id)
    send_tokens_to_user(response, access_token, refresh_token)
    return access_token, refresh_token
