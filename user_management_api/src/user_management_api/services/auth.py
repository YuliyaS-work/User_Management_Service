"""Authentication module providing handlers for user authentication,
including sign-up, login, logout and token refresh operations.
"""
from datetime import timedelta

import phonenumbers
from fastapi import HTTPException, status, Response, Request, Depends
from phonenumbers.phonenumberutil import NumberParseException
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.core.security import get_password_hash, create_access_token, create_refresh_token, \
    verify_password, decode_token, validate_refresh_token, get_token_hash
from src.user_management_api.models import User
from src.user_management_api.schemas.auth import UserRegister, UserLogin
from src.user_management_api.dao.user import UserDAO
from src.user_management_api.utils.auth import send_tokens_to_user, \
    get_access_token_from_cookie, delete_tokens_from_cookies, \
    get_refresh_token_from_cookie
from src.user_management_api.core.config import r


def create_and_store_tokens(user_id) -> tuple:
    access_token = create_access_token({"sub": user_id})
    refresh_token, jti = create_refresh_token({"sub": user_id})
    save_refresh_token_to_redis(refresh_token, jti, user_id)
    return access_token, refresh_token

def delete_refresh_token_from_redis(user_id: str, jti: str) -> None:
    """
    Delete refresh token hash and indicate jti of the refresh token is "revoked".
    """
    r.delete(f"refresh_token:{user_id}:{jti}")
    r.set(f"revoked_token:{jti}", "true")


def save_refresh_token_to_redis(refresh_token, jti, user_id) -> str:
    """
    Save refresh token hash to redis.
    """
    token_hash = get_token_hash(refresh_token)
    ttl = timedelta(days=30)
    return r.setex(f"refresh_token:{user_id}:{jti}", int(ttl.total_seconds()), token_hash)


def verify_refresh_token_and_delete(response: Response, request: Request) -> tuple:
    old_refresh_token = get_refresh_token_from_cookie(request)
    payload = decode_token(old_refresh_token)
    hash_token = get_token_hash(old_refresh_token)
    user_id, jti = validate_refresh_token(response, payload, hash_token)
    return user_id, jti


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

    return {
        "message": "User registered successfully",
        "access_token": access_token,
        "refresh_token": refresh_token,
            }


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
    filters = [User.username == user_data.login, User.email == user_data.login]

    try:
        phonenumbers.parse(user_data.login)
        filters.append(User.phone_number == user_data.login)
    except NumberParseException:
        pass

    user = await UserDAO.find_one_or_none(db, or_(*filters))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User's not found."
        )

    # Get a password.
    password_db = user.password

    verification = verify_password(user_data.password, password_db)

    if not verification:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Password's not correct for {user.username}"
        )

    # UUID to string for JSON serialization to get tokens.
    user_id = str(user.id)

    access_token, refresh_token = create_and_store_tokens(user_id)
    send_tokens_to_user(response, access_token, refresh_token)

    return {
        "message": "User logged in",
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


def logout_user(
        response: Response,
        request: Request,
) -> dict:
    """
    Log out a user.

    Args:
        response (Response): save JWT tokens in cookies.
        request (Request): get JWT tokens from cookies.
    Returns:
        dict: Message about success of log out.
    """

    user_id, jti = verify_refresh_token_and_delete(response, request)

    delete_refresh_token_from_redis(user_id, jti)

    delete_tokens_from_cookies(response)

    return {"message": "User logged out"}


def renew_tokens(request: Request, response: Response) -> dict:
    """
    Renew JWT tokens with an old refresh_token.

    Args:
        response (Response): save JWT tokens in cookies.
        request (Request): get JWT tokens from cookies.
    Returns:
        dict: Message about success of log out.
    """
    user_id, jti = verify_refresh_token_and_delete(response, request)

    delete_refresh_token_from_redis(user_id, jti)
    access_token, refresh_token = create_and_store_tokens(user_id)
    send_tokens_to_user(response, access_token, refresh_token)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }
