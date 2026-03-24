"""Authentication module providing handlers for user authentication,
including sign-up, login, logout and token refresh operations.
"""
from datetime import timedelta

import phonenumbers
from fastapi import HTTPException, status, Response, Request
from fastapi.responses import JSONResponse
from phonenumbers.phonenumberutil import NumberParseException
from sqlalchemy import or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.user_management_api.core.security import get_password_hash, create_access_token, create_refresh_token, \
    verify_password, decode_token, validate_refresh_token, get_token_hash
from src.user_management_api.models import User
from src.user_management_api.schemas.auth import UserRegister, UserLogin, TokenResponse
from src.user_management_api.dao.user import UserDAO
from src.user_management_api.utils.auth import send_tokens_to_user, delete_tokens_from_cookies, \
    get_refresh_token_from_cookie
from src.user_management_api.core.config import r


async def create_and_store_tokens(user_id) -> tuple:
    access_token = create_access_token({"sub": user_id})
    refresh_token, jti = create_refresh_token({"sub": user_id})
    await save_refresh_token_to_redis(refresh_token, jti, user_id)
    return access_token, refresh_token

async def delete_refresh_token_from_redis(user_id: str, jti: str) -> None:
    """
    Delete refresh token hash and indicate jti of the refresh token is "revoked".
    """
    await r.delete(f"refresh_token:{user_id}:{jti}")
    await r.set(f"revoked_token:{jti}", "true")


async def save_refresh_token_to_redis(refresh_token, jti, user_id) -> str:
    """
    Save refresh token hash to redis.
    """
    token_hash = get_token_hash(refresh_token)
    ttl = timedelta(days=30)
    refresh_token = await r.setex(f"refresh_token:{user_id}:{jti}", int(ttl.total_seconds()), token_hash)
    return refresh_token


async def verify_refresh_token_and_delete(response: Response, request: Request) -> tuple:
    """
    Verify refresh token from cookies to one stored in redis.
    """
    old_refresh_token = get_refresh_token_from_cookie(request)
    payload = decode_token(old_refresh_token)
    hash_token = get_token_hash(old_refresh_token)
    user_id, jti = await validate_refresh_token(response, payload, hash_token)
    return user_id, jti


async def register_user(response: Response, user_data: UserRegister, db: AsyncSession) -> TokenResponse:
    """
    Register a user and create a record in the database.

    Args:
        response (Response): save JWT tokens in cookies.
        user_data (UserRegister): Data required to create a new user in the database.
        db (AsyncSession): Database session.
    Returns:
        TokenResponse: An access and refresh tokens.
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

    # Create tokens, set tokens in cookies and a refresh token in redis.
    access_token, refresh_token = await create_and_store_tokens(user_id)
    send_tokens_to_user(response, access_token, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


async def login_user(response: Response, user_data: UserLogin, db: AsyncSession) -> TokenResponse:
    """
    Check a user and login.

    Args:
        response (Response): save JWT tokens in cookies.
        user_data (UserRegister): Data required to create a new user in the database.
        db (AsyncSession): Database session.
    Returns:
        TokenResponse: An access and refresh tokens.
    """
    # Compare the data in login field with email, username and phone number in the database.
    filters = [User.username == user_data.login, User.email == user_data.login]

    # Avoid strict correspondence of email and username with PhoneNumber type.
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

    # Create tokens, set tokens in cookies and a refresh token in redis.
    access_token, refresh_token = await create_and_store_tokens(user_id)
    send_tokens_to_user(response, access_token, refresh_token)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token
    )


async def logout_user(
        response: Response,
        request: Request,
) -> dict | JSONResponse:
    """
    Log out a user.

    Args:
        response (Response): save JWT tokens in cookies.
        request (Request): get JWT tokens from cookies.
    Returns:
        dict: Message about success of log out.
        JSONResponse: A refresh token is invalid.
    """
    try:
        user_id, jti = await verify_refresh_token_and_delete(response, request)
        await delete_refresh_token_from_redis(user_id, jti)
        return {"message": "User logged out"}

    # Raise an exception if a token is invalid.
    except HTTPException as e:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content= {"detail": str(e)}
        )
    finally:
        delete_tokens_from_cookies(response)




async def renew_tokens(request: Request, response: Response) -> TokenResponse | JSONResponse:
    """
    Renew JWT tokens with an old refresh_token.

    Args:
        response (Response): save JWT tokens in cookies.
        request (Request): get JWT tokens from cookies.
    Returns:
        TokenResponse: An access and refresh tokens.
        JSONResponse: A refresh token is invalid.
    """
    try:
        # Verify a refresh token and delete from redis.
        user_id, jti = await verify_refresh_token_and_delete(response, request)
        await delete_refresh_token_from_redis(user_id, jti)

        # Create tokens, set tokens in cookies and a refresh token in redis.
        new_access_token, new_refresh_token = await create_and_store_tokens(user_id)
        send_tokens_to_user(response, new_access_token, new_refresh_token)

        return TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token
        )

    # Raise an exception if a token is invalid.
    except HTTPException as e:
        response_refresh = JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content= {"detail": str(e)}
        )
        delete_tokens_from_cookies(response)
        return response_refresh